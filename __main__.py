from mcdreforged.api.all import *

# 创建全局实例
player_batch_instance = None

def on_load(server: PluginServerInterface, old):
    global player_batch_instance

    # 导入并创建 PlayerBatch 实例
    from player_batch.main import PlayerBatch
    player_batch_instance = PlayerBatch(server)
    player_batch_instance.on_load()

    # 注册玩家加入事件监听器 - 使用正确的事件名称
    @server.register_event_listener('mcdr.user_info_joined')
    def on_player_joined(server, player, info):
        server.logger.info(f'§6[DEBUG] 玩家加入事件触发: {player}')
        server.logger.info(f'§6[DEBUG] 事件信息: {info}')
        if player_batch_instance is not None:
            player_batch_instance.on_bot_joined(player)

    # 同时监听多个可能的事件
    @server.register_event_listener('player_joined')
    def on_player_joined_vanilla(server, player, info):
        server.logger.info(f'§6[DEBUG] player_joined事件触发: {player}')
        if player_batch_instance is not None:
            player_batch_instance.on_bot_joined(player)

def on_unload(server: PluginServerInterface):
    global player_batch_instance
    player_batch_instance = None