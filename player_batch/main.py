# main.py
from mcdreforged.api.all import *
import os
import json
import time
import threading
from typing import Dict, List, Tuple, Optional, Any

DEFAULT_CONFIG = {
    'base_name': 'bot_',
    'permission': 0,
    'interval': 1.0
}

DIRECTION_MAP = {
    '+x': ('x', 1),
    '-x': ('x', -1),
    '+z': ('z', 1),
    '-z': ('z', -1)
}

class CommandExecutor:
    """命令执行器，封装命令执行逻辑"""
    
    def __init__(self, server: PluginServerInterface, config: Dict):
        self.server = server
        self.config = config
        self.active_threads = []  # 存储活动线程
        self.stop_flag = False    # 停止标志
        
    def execute_with_interval(self, commands: List[str], src: CommandSource, 
                            success_msg: str, use_interval: bool = True) -> None:
        """以间隔执行命令列表"""
        def task():
            try:
                thread_id = threading.get_ident()
                for idx, cmd in enumerate(commands):
                    # 检查停止标志
                    if self.stop_flag:
                        self.server.logger.info(f'线程 {thread_id} 已收到停止信号，终止执行')
                        break
                    
                    if use_interval and idx > 0 and self.config['interval'] > 0:
                        # 在休眠期间也检查停止标志
                        sleep_interval = self.config['interval']
                        for _ in range(int(sleep_interval * 10)):  # 每0.1秒检查一次
                            if self.stop_flag:
                                self.server.logger.info(f'线程 {thread_id} 在休眠期间收到停止信号，终止执行')
                                return
                            time.sleep(0.1)
                    
                    self.server.execute(cmd)
                
                # 只有正常完成时才发送成功消息
                if not self.stop_flag:
                    src.reply(success_msg)
                    
            except Exception as e:
                if not self.stop_flag:  # 如果不是停止导致的异常
                    self.server.logger.error(f'命令执行出错: {str(e)}')
                    src.reply('§c命令执行失败，请查看日志')
            finally:
                # 从活动线程列表中移除
                with threading.Lock():
                    if threading.current_thread() in self.active_threads:
                        self.active_threads.remove(threading.current_thread())
                
        # 创建并启动线程
        thread = threading.Thread(target=task, daemon=True)
        with threading.Lock():
            self.active_threads.append(thread)
        thread.start()
    
    def stop_all(self) -> bool:
        """停止所有正在执行的批量操作，不发送任何消息"""
        if not self.active_threads:
            return False
            
        self.stop_flag = True
        stopped_count = len(self.active_threads)
        self.server.logger.info(f'正在停止 {stopped_count} 个批量操作线程...')
        
        # 等待所有线程结束（最多等待5秒）
        start_time = time.time()
        for thread in list(self.active_threads):  # 使用副本避免修改时迭代
            try:
                thread.join(timeout=2)
            except:
                pass
        
        # 重置停止标志
        self.stop_flag = False
        self.active_threads.clear()
        
        elapsed = time.time() - start_time
        self.server.logger.info(f'已停止所有批量操作，耗时 {elapsed:.2f} 秒')
        return True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.config_file = os.path.join(server.get_data_folder(), 'player_batch.json')
        self.config = DEFAULT_CONFIG.copy()
        
    def load(self) -> Dict:
        """加载配置"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            if not os.path.exists(self.config_file):
                self.save()
                
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                self.config = {**DEFAULT_CONFIG, **loaded_config}
                
            # 验证配置
            self.config['permission'] = max(0, int(self.config.get('permission', 0)))
            self.config['interval'] = max(0.0, float(self.config.get('interval', 1.0)))
            
            self.save()
            self.server.logger.debug('配置加载成功')
            
        except Exception as e:
            self.server.logger.error(f'配置加载失败: {e}')
            self.config = DEFAULT_CONFIG.copy()
            
        return self.config
    
    def save(self) -> None:
        """保存配置"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.server.logger.error(f'配置保存失败: {e}')


class PlayerBatch:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.config_manager = ConfigManager(server)
        self.command_executor = None
        self.config = None
        
    def on_load(self):
        """插件加载时调用"""
        self.config = self.config_manager.load()
        self.command_executor = CommandExecutor(self.server, self.config)
        self.register_commands()
        self.register_help_messages()
        self.server.logger.info('§a插件初始化完成')
        
    def register_help_messages(self):
        """注册帮助消息"""
        for cmd in ['!!playerbatch', '!!plb']:
            self.server.register_help_message(
                cmd,
                f"§6批量操作假人 §7输入 §e{cmd} §7查看完整帮助"
            )
            self.server.logger.info(f'已注册命令 {cmd}')
    
    def register_commands(self):
        """注册所有命令"""
        def create_command(root: str):
            builder = Literal(root) \
                .requires(lambda src: src.has_permission(self.config['permission'])) \
                .runs(self.show_help)
            
            # 基础命令
            builder = builder.then(
                QuotableText('name').then(
                    Integer('start').then(
                        Integer('end').then(
                            GreedyText('action_args').runs(self.process_command)
                        )
                    )
                )
            )
            
            # 直线生成命令
            builder = builder.then(
                Literal('l').then(
                    QuotableText('name').then(
                        Integer('start').then(
                            Integer('length').then(
                                QuotableText('direction').then(
                                    Number('interval').runs(self.process_line_command)
                                )
                            )
                        )
                    )
                )
            )
            
            # 方形阵列命令
            builder = builder.then(
                Literal('s').then(
                    QuotableText('name').then(
                        Integer('start').then(
                            Integer('long').then(
                                Integer('width').then(
                                    QuotableText('direction1').then(
                                        QuotableText('direction2').then(
                                            Number('interval').runs(self.process_square_command)
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            
            # 初始化序列命令
            builder = builder.then(
                Literal('init').then(
                    QuotableText('name').then(
                        Integer('start').then(
                            Integer('length').then(
                                Number('interval1').then(
                                    Number('interval2').then(
                                        Number('x').then(
                                            Number('y').then(
                                                Number('z').then(
                                                    GreedyText('action').runs(self.process_init_command)
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
            
            # 停止命令
            builder = builder.then(
                Literal('stop').runs(self.process_stop_command)
            )
            
            return builder
        
        for cmd in ['!!playerbatch', '!!plb']:
            self.server.register_command(create_command(cmd))
    
    def show_help(self, src: CommandSource):
        """显示帮助信息"""
        help_msgs = [
            '§6==== PlayerBatch 帮助 ====',
            '§6!!plb §7或 §6!!playerbatch §7- 显示本帮助信息',
            '§6基础命令:',
            '§7!!plb <名称> <起始> <结束> <动作> §e- 批量操作假人',
            '§6直线生成:',
            '§7!!plb l <名称> <起始> <长度> <方向> <间隔> §e- 生成直线排列假人',
            '§e方向参数: §a+x, -x, +z, -z',
            '§6方形阵列:',
            '§7!!plb s <名称> <起始> <长> <宽> <方向1> <方向2> <间隔> §e- 生成二维排列假人',
            '§6初始化序列:',
            '§7!!plb init <名称> <起始> <长度> <间隔1> <间隔2> <x> <y> <z> <动作> §e- 生成假人并依次执行动作和退出，间隔控制',
            '§6停止命令:',
            '§7!!plb stop',
            '§e示例:',
            '§7!!plb l bot 1 5 +x 1 §e- 生成bot1到bot5，每个向东间隔1格',
            '§7!!plb s bot 1 2 3 +x +z 1 §e- 生成bot1到bot6，在X/Z平面形成2x3方阵',
            '§7!!plb init bot 1 3 1 2 0 100 0 kill §e- 生成bot1-3在(0,100,0)，每个生成后立即kill，间隔1秒后退出，间隔2秒处理下一个',
            f'§a当前生成间隔: §e{self.config["interval"]}秒'
        ]
        src.reply('\n'.join(help_msgs))
    
    def _build_bot_name(self, base_name: str, name: str, index: int) -> str:
        """构建假人名称"""
        return f'{base_name}{name}{index}'
    
    def _build_player_command(self, src: CommandSource, bot_name: str, action: str) -> str:
        """构建玩家命令"""
        if src.is_player:
            return f'/execute as {src.player} at @s run player {bot_name} {action}'
        return f'/player {bot_name} {action}'
    
    def process_command(self, src: CommandSource, ctx: dict):
        """处理基础命令"""
        try:
            name = ctx['name']
            start = ctx['start']
            end = ctx['end']
            action_args = ctx['action_args'].strip()
            base = self.config['base_name']
            
            if start > end:
                src.reply('§c错误：起始值不能大于结束值')
                return
            
            is_spawn = action_args.lower().startswith('spawn')
            use_interval = is_spawn
            interval_info = f'（间隔 {self.config["interval"]}秒）' if is_spawn else ''
            
            commands = []
            for i in range(start, end + 1):
                bot_name = self._build_bot_name(base, name, i)
                cmd = self._build_player_command(src, bot_name, action_args)
                commands.append(cmd)
            
            success_msg = f'§a已操作假人 {base}{name}[{start}-{end}] 的 {action_args} 指令{interval_info}'
            self.command_executor.execute_with_interval(commands, src, success_msg, use_interval)
            
        except Exception as e:
            self.server.logger.error(f'执行出错: {str(e)}')
            src.reply('§c命令执行失败，请查看日志')
    
    def parse_direction(self, direction: str) -> Tuple[Optional[str], Optional[int]]:
        """解析方向参数"""
        return DIRECTION_MAP.get(direction, (None, None))
    
    def _build_spawn_command(self, src: CommandSource, bot_name: str, coord: str) -> str:
        """构建生成命令"""
        if src.is_player:
            return f'/execute as {src.player} at @s positioned {coord} positioned over world_surface run player {bot_name} spawn'
        return f'/execute positioned {coord} positioned over world_surface run player {bot_name} spawn'
    
    def process_line_command(self, src: CommandSource, ctx: dict):
        """处理直线生成命令"""
        try:
            name = ctx['name']
            start = ctx['start']
            length = ctx['length']
            direction = ctx['direction']
            interval = ctx['interval']
            base = self.config['base_name']
            
            if length < 1:
                src.reply('§c错误：长度必须≥1')
                return
            
            end = start + length - 1
            axis, sign = self.parse_direction(direction)
            
            if axis is None:
                src.reply(f'§c错误的方向参数：{direction}')
                return
            
            commands = []
            for i in range(start, end + 1):
                bot_name = self._build_bot_name(base, name, i)
                offset = (i - start) * interval * sign
                coord = f'~{offset} ~ ~' if axis == 'x' else f'~ ~ ~{offset}'
                cmd = self._build_spawn_command(src, bot_name, coord)
                commands.append(cmd)
            
            success_msg = (f'§a成功生成直线假人 {base}{name}[{start}-{end}]，'
                          f'方向 {direction} 间隔 {interval}格（命令间隔 {self.config["interval"]}秒）')
            self.command_executor.execute_with_interval(commands, src, success_msg, True)
            
        except Exception as e:
            self.server.logger.error(f'直线生成出错: {str(e)}')
            src.reply('§c直线生成失败，请查看日志')
    
    def process_square_command(self, src: CommandSource, ctx: dict):
        """处理方形阵列命令"""
        try:
            name = ctx['name']
            start = ctx['start']
            long = ctx['long']
            width = ctx['width']
            dir1 = ctx['direction1']
            dir2 = ctx['direction2']
            interval = ctx['interval']
            base = self.config['base_name']
            
            if long < 1 or width < 1:
                src.reply('§c错误：长和宽必须≥1')
                return
            
            total = long * width
            end = start + total - 1
            axis1, sign1 = self.parse_direction(dir1)
            axis2, sign2 = self.parse_direction(dir2)
            
            if axis1 is None or axis2 is None:
                src.reply(f'§c错误的方向参数：{dir1} 或 {dir2}')
                return
            
            commands = []
            for idx in range(total):
                i = start + idx
                bot_name = self._build_bot_name(base, name, i)
                
                x_offset = 0.0
                z_offset = 0.0
                row = idx // width
                col = idx % width
                
                if axis1 == 'x':
                    x_offset += row * interval * sign1
                elif axis1 == 'z':
                    z_offset += row * interval * sign1
                
                if axis2 == 'x':
                    x_offset += col * interval * sign2
                elif axis2 == 'z':
                    z_offset += col * interval * sign2
                
                coord = f'~{x_offset} ~ ~{z_offset}'
                cmd = self._build_spawn_command(src, bot_name, coord)
                commands.append(cmd)
            
            success_msg = (f'§a成功生成方阵假人 {base}{name}[{start}-{end}]，'
                          f'方向 {dir1}×{dir2} 间隔 {interval}格（命令间隔 {self.config["interval"]}秒）')
            self.command_executor.execute_with_interval(commands, src, success_msg, True)
            
        except Exception as e:
            self.server.logger.error(f'方阵生成出错: {str(e)}')
            src.reply('§c方阵生成失败，请查看日志')
    
    def process_init_command(self, src: CommandSource, ctx: dict):
        """处理初始化序列命令"""
        try:
            name = ctx['name']
            start = ctx['start']
            length = ctx['length']
            interval1 = ctx['interval1']
            interval2 = ctx['interval2']
            x = ctx['x']
            y = ctx['y']
            z = ctx['z']
            action = ctx['action'].strip()
            base = self.config['base_name']
            
            if length < 1:
                src.reply('§c错误：长度必须≥1')
                return
            
            end = start + length - 1
            
            def task():
                try:
                    player_name = src.player if src.is_player else None
                    
                    for i in range(start, end + 1):
                        # 检查停止标志
                        if self.command_executor.stop_flag:
                            return
                        
                        bot_name = self._build_bot_name(base, name, i)
                        
                        # 生成假人
                        spawn_cmd = f'/execute positioned {x} {y} {z} run player {bot_name} spawn'
                        if player_name:
                            spawn_cmd = f'/execute as {player_name} at @s positioned {x} {y} {z} run player {bot_name} spawn'
                        self.server.execute(spawn_cmd)
                        
                        # 检查停止标志
                        if self.command_executor.stop_flag:
                            return
                        
                        # 执行动作
                        action_cmd = f'/player {bot_name} {action}'
                        self.server.execute(action_cmd)
                        
                        # 检查停止标志
                        if self.command_executor.stop_flag:
                            return
                        
                        # 等待间隔1
                        if interval1 > 0:
                            # 在等待期间检查停止标志
                            for _ in range(int(interval1 * 10)):
                                if self.command_executor.stop_flag:
                                    return
                                time.sleep(0.1)
                        
                        # 检查停止标志
                        if self.command_executor.stop_flag:
                            return
                        
                        # 杀死假人
                        kill_cmd = f'/player {bot_name} kill'
                        self.server.execute(kill_cmd)
                        
                        # 如果不是最后一个，等待间隔2
                        if i != end and interval2 > 0:
                            # 在等待期间检查停止标志
                            for _ in range(int(interval2 * 10)):
                                if self.command_executor.stop_flag:
                                    return
                                time.sleep(0.1)
                    
                    src.reply(f'§a成功处理假人序列 {base}{name}[{start}-{end}]，'
                            f'动作间隔 {interval1}秒，循环间隔 {interval2}秒')
                    
                except Exception as e:
                    if not self.command_executor.stop_flag:  # 如果不是停止导致的异常
                        self.server.logger.error(f'初始化命令执行出错: {str(e)}')
                        src.reply('§c初始化命令执行失败，请查看日志')
            
            # 创建并管理线程
            thread = threading.Thread(target=task, daemon=True)
            with threading.Lock():
                self.command_executor.active_threads.append(thread)
            thread.start()
            
        except Exception as e:
            self.server.logger.error(f'初始化命令解析出错: {str(e)}')
            src.reply('§c命令格式错误，请检查参数')
    
    def process_stop_command(self, src: CommandSource):
        """处理停止命令 - 不发送任何提示消息"""
        self.command_executor.stop_all()
        # 不发送任何回复消息


def on_load(server: PluginServerInterface, old):
    """插件加载入口"""
    PlayerBatch(server).on_load()