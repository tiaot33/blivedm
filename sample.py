# -*- coding: utf-8 -*-
import asyncio
import datetime
import random
from configparser import ConfigParser

import pytz
import requests
from corpwechatbot.app import AppMsgSender

import blivedm

cfg = ConfigParser()
cfg.read('config.ini')
CQHTTP_HOST = cfg.get('notify_qq', 'cqhttp_host')
app = AppMsgSender(corpid=cfg.get('notify_wx', 'corpid'),  # 你的企业id
                   corpsecret=cfg.get('notify_wx', 'corpsecret'),  # 你的应用凭证密钥
                   agentid=cfg.get('notify_wx', 'agentid'))  # 你的应用id
# app.send_text('我已回归')
# 直播间ID的取值看直播间URL
TEST_ROOM_IDS = [22603245]
watch_users = {1265680561}


def send_guild_message(guild_id: int, channel_id: int, mes: str):
    res = requests.post(f'{CQHTTP_HOST}/send_guild_channel_msg', json={
        'guild_id': guild_id,
        'channel_id': channel_id,
        'message': mes
    })


def send_group_msg(msg: str):
    res = requests.post(f'{CQHTTP_HOST}/send_group_msg', json={
        'group_id': cfg.get('notify_qq', 'group_id'),
        'message': msg,
        'auto_escape': False
    })


async def main():
    # await run_single_client()
    await run_multi_client()


async def run_single_client():
    """
    演示监听一个直播间
    """
    room_id = random.choice(TEST_ROOM_IDS)
    # 如果SSL验证失败就把ssl设为False，B站真的有过忘续证书的情况
    client = blivedm.BLiveClient(room_id, ssl=True)
    handler = MyHandler()
    client.add_handler(handler)

    client.start()
    try:
        # 演示5秒后停止
        await asyncio.sleep(5)
        client.stop()

        await client.join()
    finally:
        await client.stop_and_close()


live_info_g = {}


async def run_multi_client():
    """
    演示同时监听多个直播间
    """
    clients = [blivedm.BLiveClient(room_id) for room_id in TEST_ROOM_IDS]
    handler = MyHandler()
    for client in clients:
        client.add_handler(handler)
        client.start()

    try:
        await asyncio.gather(*(
            client.join() for client in clients
        ))
    finally:
        await asyncio.gather(*(
            client.stop_and_close() for client in clients
        ))


class MyHandler(blivedm.BaseHandler):
    # 演示如何添加自定义回调
    _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()

    # 入场消息回调
    async def __interact_word_callback(self, client: blivedm.BLiveClient, command: dict):
        # print(f"[{client.room_id}] INTERACT_WORD: self_type={type(self).__name__}, room_id={client.room_id}, uname={command['data']['uname']}")
        if command['data']['uid'] in watch_users:
            # command['data']['timestamp']
            t = datetime.datetime.fromtimestamp(command['data']['timestamp'], pytz.timezone('Asia/Shanghai')).strftime(
                '%Y-%m-%d %H:%M:%S')
            app.send_text(
                content=f"{command['data']['uname']}({command['data']['uid']}) 进入了直播间({client.room_id}) [{t}]")

    _CMD_CALLBACK_DICT['INTERACT_WORD'] = __interact_word_callback  # noqa

    # LIVE
    async def __live_callback(self, client: blivedm.BLiveClient, command: dict):
        if 'live_key'not in live_info_g or command['live_key'] != live_info_g['live_key']:
            i = command['sub_session_key'].index(':')
            timestamp = int(command['sub_session_key'][i + 1:])
            live_info_g['live_time'] = timestamp
            t = datetime.datetime.fromtimestamp(timestamp, pytz.timezone('Asia/Shanghai')) \
                .strftime('%Y-%m-%d %H:%M:%S')
            app.send_text(f'直播间({client.room_id})开播了[{t}]')

    _CMD_CALLBACK_DICT['LIVE'] = __live_callback

    # ROOM_CHANGE
    async def __room_change_callback(self, client: blivedm.BLiveClient, command: dict):
        app.send_text(content=f"[{client.room_id}]直播间信息变为 {command['data']['title']} "
                              f"所在分区({command['data']['parent_area_name']}_{command['data']['area_name']})")

    _CMD_CALLBACK_DICT['ROOM_CHANGE'] = __room_change_callback  # noqa

    # ROOM_ADMIN_REVOKE
    async def __room_admin_revoke_callback(self, client: blivedm.BLiveClient, command: dict):
        app.send_text(content=f"[{client.room_id}]直播间 {command['msg']} uid=[{command['uid']}]")

    _CMD_CALLBACK_DICT['ROOM_ADMIN_REVOKE'] = __room_admin_revoke_callback  # noqa

    # room_admin_entrance
    async def __room_admin_entrance_callback(self, client: blivedm.BLiveClient, command: dict):
        app.send_text(content=f"[{client.room_id}]直播间 {command['msg']} uid=[{command['uid']}]")

    _CMD_CALLBACK_DICT['room_admin_entrance'] = __room_admin_revoke_callback  # noqa

    # WARNING
    async def __warning_callback(self, client: blivedm.BLiveClient, command: dict):
        app.send_text(content=f"[{client.room_id}]直播间 收到了警告:{command['msg']}")

    _CMD_CALLBACK_DICT['WARNING'] = __warning_callback

    # CUT_OFF
    async def __cut_off_callback(self, client: blivedm.BLiveClient, command: dict):
        app.send_text(content=f"[{client.room_id}]直播间 被切断了直播:{command['msg']}")

    _CMD_CALLBACK_DICT['CUT_OFF'] = __cut_off_callback

    # ROOM_BLOCK_MSG
    async def __room_block_msg_callback(self, client: blivedm.BLiveClient, command: dict):
        # app.send_text(content=f"[{client.room_id}]直播间 {command['data']['uname']}({command['data']['uid']})被房管大人封禁")
        send_group_msg(f"[{client.room_id}]直播间 {command['data']['uname']}({command['data']['uid']})被房管大人封禁")

    _CMD_CALLBACK_DICT['ROOM_BLOCK_MSG'] = __room_block_msg_callback

    async def _on_heartbeat(self, client: blivedm.BLiveClient, message: blivedm.HeartbeatMessage):
        # print(f'[{client.room_id}] 当前人气值：{message.popularity}')
        pass

    async def _on_danmaku(self, client: blivedm.BLiveClient, message: blivedm.DanmakuMessage):
        # print(f'[{client.room_id}] {message.uname}：{message.msg}')
        if message.uid in watch_users:
            app.send_text(content=f'[{client.room_id}] {message.uname}：{message.msg}')

    async def _on_gift(self, client: blivedm.BLiveClient, message: blivedm.GiftMessage):
        # print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
        #       f' （{message.coin_type}瓜子x{message.total_coin}）')
        pass

    async def _on_buy_guard(self, client: blivedm.BLiveClient, message: blivedm.GuardBuyMessage):
        # print(f'[{client.room_id}] {message.username} 购买{message.gift_name}')
        pass

    async def _on_super_chat(self, client: blivedm.BLiveClient, message: blivedm.SuperChatMessage):
        # print(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')
        pass


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
