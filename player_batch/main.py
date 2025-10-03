from mcdreforged.api.all import *
import os
import json
import time
import threading

DEFAULT_CONFIG = {
    'base_name': 'bot_',
    'permission': 0,
    'interval': 1.0
}


class PlayerBatch:
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.config = None
        self.config_file = os.path.join(server.get_data_folder(), 'player_batch.json')
        # 新增：假人动作队列
        self.pending_actions = {}  # {bot_name: [action_commands]}
        self.processing_bots = set()  # 正在处理的假人
        # 新增：全局停止标志
        self.stop_cmd = False

    def on_load(self):
        self.load_config()
        self.register_commands()
        self.server.logger.info('§a插件初始化完成')

    def on_bot_joined(self, player_name: str):
        """当假人加入游戏时调用"""
        # 调试信息
        self.server.logger.info(f'§6[DEBUG] === 进入on_bot_joined方法 ===')
        self.server.logger.info(f'§6[DEBUG] 加入的玩家: {player_name}')
        self.server.logger.info(f'§6[DEBUG] 当前等待队列: {list(self.pending_actions.keys())}')
        self.server.logger.info(f'§6[DEBUG] 正在处理的假人: {self.processing_bots}')

        # 检查是否是我们要处理的假人
        for bot_name in list(self.pending_actions.keys()):
            self.server.logger.info(f'§6[DEBUG] 比较: "{player_name}" == "{bot_name}" -> {player_name == bot_name}')
            if player_name == bot_name:
                self.server.logger.info(f'§a[SUCCESS] 匹配成功！检测到假人 {player_name} 加入游戏，开始执行动作')

                def execute_actions():
                    time.sleep(0.2)  # 额外等待0.2秒确保稳定
                    if bot_name in self.pending_actions:
                        actions = self.pending_actions[bot_name]
                        self.server.logger.info(f'§a[SUCCESS] 开始执行假人 {bot_name} 的 {len(actions)} 个动作')

                        for action in actions:
                            try:
                                self.server.logger.info(f'§a执行假人 {bot_name} 动作: {action}')
                                self.server.execute(action)
                                time.sleep(0.1)  # 动作间小间隔
                            except Exception as e:
                                self.server.logger.error(f'§c执行假人 {bot_name} 动作失败: {e}')

                        # 清理队列
                        del self.pending_actions[bot_name]
                        self.processing_bots.discard(bot_name)
                        self.server.logger.info(f'§a假人 {bot_name} 动作执行完成')
                    else:
                        self.server.logger.warning(f'§e假人 {bot_name} 不在等待队列中，可能已超时清理')

                threading.Thread(target=execute_actions, daemon=True).start()
                break  # 找到匹配的假人就退出循环
        else:
            self.server.logger.info(f'§6[DEBUG] 玩家 {player_name} 不在等待队列中')

    def add_bot_action(self, bot_name: str, action_commands: list):
        """添加假人动作到队列"""
        self.server.logger.info(f'§6添加假人动作: {bot_name} -> {action_commands}')
        self.pending_actions[bot_name] = action_commands
        self.processing_bots.add(bot_name)

        # 设置超时清理（防止假人永远不加入）
        def cleanup_timeout():
            time.sleep(10)  # 10秒超时
            if bot_name in self.pending_actions:
                # 安全地获取在线玩家列表
                try:
                    minecraft_data_api = self.server.get_plugin_instance("minecraft_data_api")
                    if minecraft_data_api:
                        online_players = minecraft_data_api.get_server_player_list()
                    else:
                        online_players = "Minecraft Data API 未加载"
                except Exception as e:
                    online_players = f"获取失败: {e}"

                self.server.logger.warning(f'§e假人 {bot_name} 在10秒内未加入游戏，清理动作队列')
                self.server.logger.warning(f'§e当前在线玩家: {online_players}')

                del self.pending_actions[bot_name]
                self.processing_bots.discard(bot_name)

        threading.Thread(target=cleanup_timeout, daemon=True).start()

    def register_commands(self):
        def create_command(root: str):
            return Literal(root) \
                .requires(lambda src: src.has_permission(self.config['permission'])) \
                .runs(self.show_help) \
                .then(
                QuotableText('name').then(
                    Integer('start').then(
                        Integer('end').then(
                            GreedyText('action_args').runs(self.process_command)
                        )
                    )
                )
            ).then(
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
            ).then(
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
            ).then(
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
            ).then(  # 新增 stop 命令
                Literal('stop').runs(self.process_stop_command)
            )

        for cmd in ['!!playerbatch', '!!plb']:
            self.server.register_help_message(
                cmd,
                "§6批量操作假人 §7输入 §e{} §7查看完整帮助".format(cmd)
            )
            self.server.register_command(create_command(cmd))
            self.server.logger.info(f'§6已注册命令 {cmd}')

    def load_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            if not os.path.exists(self.config_file):
                with open(self.config_file, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)

            with open(self.config_file) as f:
                self.config = {**DEFAULT_CONFIG, **json.load(f)}
                if not isinstance(self.config['permission'], int) or self.config['permission'] < 0:
                    self.config['permission'] = 0
                if not isinstance(self.config['interval'], (int, float)) or self.config['interval'] < 0:
                    self.config['interval'] = 1.0
            self.save_config()
        except Exception as e:
            self.server.logger.error(f'§c配置加载失败: {e}')
            self.config = DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def show_help(self, src: CommandSource):
        help_msg = [
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
            '§6停止命令:',  # 新增停止命令帮助
            '§7!!plb stop §e- 停止所有正在执行的假人生成',
            '§e示例:',
            '§7!!plb l bot 1 5 +x 1 §e- 生成bot1到bot5，每个向东间隔1格',
            '§7!!plb s bot 1 2 3 +x +z 1 §e- 生成bot1到bot6，在X/Z平面形成2x3方阵',
            '§7!!plb init bot 1 3 1 2 0 100 0 kill §e- 生成bot1-3在(0,100,0)，每个生成后立即kill，间隔1秒后退出，间隔2秒处理下一个',
            f'§a当前生成间隔: §e{self.config["interval"]}秒'
        ]
        src.reply('\n'.join(help_msg))

    def process_stop_command(self, src: CommandSource):
        """停止所有正在执行的命令"""
        try:
            # 设置停止标志
            self.stop_cmd = True

            # 记录被停止的假人数量
            stopped_count = len(self.pending_actions)
            stopped_bots = list(self.pending_actions.keys())

            # 清空队列
            self.pending_actions.clear()
            self.processing_bots.clear()

            # 回复用户
            src.reply('§a已发送停止信号，将停止后续假人生成')
            if stopped_count > 0:
                self.server.logger.info(
                    f'§a用户 {src.player if src.is_player else "控制台"} 停止了 {stopped_count} 个假人的生成')

        except Exception as e:
            self.server.logger.error(f'§c停止命令执行出错: {str(e)}')
            src.reply('§c停止命令执行失败，请查看日志')

    def __execute_commands(self, commands: list, src: CommandSource, reply_msg: str, use_interval: bool):
        def task():
            try:
                for idx, cmd in enumerate(commands):
                    # 检查停止标志
                    if self.stop_cmd:
                        self.stop_cmd = False  # 重置停止标志
                        self.server.logger.info('§a检测到停止信号，停止执行后续命令')
                        src.reply('§a已停止后续假人生成')
                        return

                    if use_interval and idx > 0 and self.config['interval'] > 0:
                        time.sleep(self.config['interval'])
                    self.server.execute(cmd)
                src.reply(reply_msg)
            except Exception as e:
                self.server.logger.error(f'§c命令执行出错: {str(e)}')
                src.reply('§c命令执行失败，请查看日志')

        threading.Thread(target=task, daemon=True).start()

    def process_command(self, src: CommandSource, ctx: dict):
        try:
            name = ctx['name']
            start = ctx['start']
            end = ctx['end']
            action_args = ctx['action_args']
            base = self.config['base_name']

            if start > end:
                return src.reply('§c错误：起始值不能大于结束值')

            is_spawn = action_args.strip().lower().startswith('spawn')
            use_interval = is_spawn
            interval_info = f'（间隔 {self.config["interval"]}秒）' if is_spawn else ''

            commands = []
            for i in range(start, end + 1):
                bot_name = f'{base}{name}{i}'
                if src.is_player:
                    player_name = src.player
                    cmd = f'/execute as {player_name} at @s run player {bot_name} {action_args}'
                else:
                    cmd = f'/player {bot_name} {action_args}'
                commands.append(cmd)

            self.__execute_commands(
                commands,
                src,
                f'§a已操作假人 {base}{name}[{start}-{end}] 的 {action_args} 指令{interval_info}',
                use_interval
            )

        except Exception as e:
            self.server.logger.error(f'§c执行出错: {str(e)}')
            src.reply('§c命令执行失败，请查看日志')

    def parse_direction(self, direction: str):
        valid = {
            '+x': ('x', 1),
            '-x': ('x', -1),
            '+z': ('z', 1),
            '-z': ('z', -1)
        }
        return valid.get(direction, (None, None))

    def process_line_command(self, src: CommandSource, ctx: dict):
        try:
            name = ctx['name']
            start = ctx['start']
            length = ctx['length']
            direction = ctx['direction']
            interval = ctx['interval']
            base = self.config['base_name']

            if length < 1:
                return src.reply('§c错误：长度必须≥1')
            end = start + length - 1

            axis, sign = self.parse_direction(direction)
            if axis is None:
                return src.reply(f'§c错误的方向参数：{direction}')

            commands = []
            for i in range(start, end + 1):
                bot_name = f'{base}{name}{i}'
                offset = (i - start) * interval * sign
                if axis == 'x':
                    coord = f'~{offset} ~ ~'
                else:
                    coord = f'~ ~ ~{offset}'

                full_action = 'spawn'
                if src.is_player:
                    player_name = src.player
                    cmd = f'/execute as {player_name} at @s positioned {coord} positioned over world_surface run player {bot_name} {full_action}'
                else:
                    cmd = f'/execute positioned {coord} positioned over world_surface run player {bot_name} {full_action}'
                commands.append(cmd)

            self.__execute_commands(
                commands,
                src,
                f'§a成功生成直线假人 {base}{name}[{start}-{end}]，方向 {direction} 间隔 {interval}格（命令间隔 {self.config["interval"]}秒）',
                True
            )

        except Exception as e:
            self.server.logger.error(f'§c直线生成出错: {str(e)}')
            src.reply('§c直线生成失败，请查看日志')

    def process_square_command(self, src: CommandSource, ctx: dict):
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
                return src.reply('§c错误：长和宽必须≥1')
            total = long * width
            end = start + total - 1

            axis1, sign1 = self.parse_direction(dir1)
            axis2, sign2 = self.parse_direction(dir2)
            if None in [axis1, axis2]:
                return src.reply(f'§c错误的方向参数：{dir1} 或 {dir2}')

            commands = []
            for idx in range(total):
                i = start + idx
                bot_name = f'{base}{name}{i}'

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
                full_action = 'spawn'

                if src.is_player:
                    player_name = src.player
                    cmd = f'/execute as {player_name} at @s positioned {coord} positioned over world_surface run player {bot_name} {full_action}'
                else:
                    cmd = f'/execute positioned {coord} positioned over world_surface run player {bot_name} {full_action}'
                commands.append(cmd)

            self.__execute_commands(
                commands,
                src,
                f'§a成功生成方阵假人 {base}{name}[{start}-{end}]，方向 {dir1}×{dir2} 间隔 {interval}格（命令间隔 {self.config["interval"]}秒）',
                True
            )

        except Exception as e:
            self.server.logger.error(f'§c方阵生成出错: {str(e)}')
            src.reply('§c方阵生成失败，请查看日志')

    def process_init_command(self, src: CommandSource, ctx: dict):
        try:
            name = ctx['name']
            start = ctx['start']
            length = ctx['length']
            interval1 = ctx['interval1']  # 动作间隔
            interval2 = ctx['interval2']  # 循环间隔
            x = ctx['x']
            y = ctx['y']
            z = ctx['z']
            action = ctx['action'].strip()
            base = self.config['base_name']

            if length < 1:
                return src.reply('§c错误：长度必须≥1')
            end = start + length - 1

            # 重置停止标志
            self.stop_cmd = False

            def task():
                try:
                    for i in range(start, start + length):
                        # 检查停止标志
                        if self.stop_cmd:
                            self.stop_cmd = False  # 重置停止标志
                            self.server.logger.info('§a检测到停止信号，停止执行后续假人生成')
                            src.reply(f'§a已停止假人生成，当前完成到 {base}{name}{i - 1}')
                            return

                        bot_name = f'{base}{name}{i}'
                        self.server.logger.info(f'§6[DEBUG] 开始处理假人: {bot_name}')

                        # 生成假人命令
                        if src.is_player:
                            player_name = src.player
                            spawn_cmd = f'/execute as {player_name} at @s positioned {x} {y} {z} run player {bot_name} spawn'
                            kill_cmd = f'/execute as {player_name} at @s run player {bot_name} kill'
                        else:
                            spawn_cmd = f'/execute positioned {x} {y} {z} run player {bot_name} spawn'
                            kill_cmd = f'/player {bot_name} kill'

                        # 动作命令
                        action_cmd = f'/player {bot_name} {action}'

                        # 准备动作队列
                        action_commands = [action_cmd]
                        self.add_bot_action(bot_name, action_commands)

                        # 执行生成命令
                        self.server.logger.info(f'§a执行生成命令: {spawn_cmd}')
                        self.server.execute(spawn_cmd)

                        # 方法1：轮询检测假人是否在线
                        self.server.logger.info(f'§6[DEBUG] 开始轮询检测假人 {bot_name} 是否在线')
                        joined = False
                        for attempt in range(30):  # 最多检测30次，每次0.5秒，总共15秒
                            # 检查停止标志
                            if self.stop_cmd:
                                self.stop_cmd = False  # 重置停止标志
                                self.server.logger.info('§a检测到停止信号，停止执行后续假人生成')
                                src.reply(f'§a已停止假人生成，当前完成到 {base}{name}{i - 1}')
                                return

                            time.sleep(0.5)
                            try:
                                minecraft_data_api = self.server.get_plugin_instance("minecraft_data_api")
                                if minecraft_data_api:
                                    online_players = minecraft_data_api.get_server_player_list()
                                    if bot_name in online_players.players:
                                        self.server.logger.info(f'§a[SUCCESS] 通过轮询检测到假人 {bot_name} 在线')
                                        # 手动触发动作执行
                                        self.on_bot_joined(bot_name)
                                        joined = True
                                        break
                            except Exception as e:
                                self.server.logger.error(f'§c轮询检测出错: {e}')

                        if not joined:
                            self.server.logger.warning(f'§e假人 {bot_name} 在15秒内未检测到在线')

                        if interval1 > 0:
                            self.server.logger.info(f'§6等待动作间隔 {interval1} 秒')
                            time.sleep(interval1)

                        # 执行kill命令
                        self.server.logger.info(f'§a执行kill命令: {kill_cmd}')
                        self.server.execute(kill_cmd)

                        # 循环间隔（最后一个假人不等待）
                        if i != end:
                            time.sleep(interval2)

                    src.reply(
                        f'§a成功处理假人序列 {base}{name}[{start}-{end}]，动作间隔 {interval1}秒，循环间隔 {interval2}秒')

                except Exception as e:
                    self.server.logger.error(f'§c初始化命令执行出错: {str(e)}')
                    src.reply('§c初始化命令执行失败，请查看日志')

            threading.Thread(target=task, daemon=True).start()

        except Exception as e:
            self.server.logger.error(f'§c初始化命令解析出错: {str(e)}')
            src.reply('§c命令格式错误，请查看日志')


def on_load(server: PluginServerInterface, old):
    PlayerBatch(server).on_load()