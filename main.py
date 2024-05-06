import os
import asyncio
import aiofiles as aiof
import time
from dotenv import load_dotenv

from twitchAPI.twitch import Twitch
from twitchAPI.helper import limit
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand

load_dotenv()

config = {
    'id': os.environ['CLIENT_ID'],
    'secret': os.environ['CLIENT_SECRET'],
    'scope': [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.CHANNEL_MODERATE],
    'token': os.environ['TOKEN'],
    'refresh_token': os.environ['REFRESH_TOKEN'],
    'channel': 'stream_guard_bot'
}


async def on_ready(ready_event: EventData):
    print('Joining channels')
    await ready_event.chat.join_room(config['channel'])


async def on_message(msg: ChatMessage):
    async with aiof.open(f'{msg.room.name}.txt', 'a') as out_file:
        await out_file.write(f'{msg.sent_timestamp}, {msg.user.name}, {msg.text}\n')
        await out_file.flush()

    print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')


async def get_streams(twitch):
    stream_iterator = twitch.get_streams(
        first=100,
        language='en',
        stream_type='live'
    )
    
    streams = []
    async for stream in limit(stream_iterator, 1):
        streams.append(stream)

    return streams

async def run():
    twitch = await Twitch(config['id'], config['secret'])
    await twitch.set_user_authentication(
        config['token'],
        config['scope'],
        config['refresh_token']
    )

    streams = await get_streams(twitch)
    chat = await Chat(twitch)

    # register the handlers for the events you want
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)

    chat.start()
    tmp = await chat.join_room(streams[0].user_name)
    print(tmp)

    try:
        input('press ENTER to stop\n')
    finally:
        chat.stop()
        await twitch.close()

asyncio.run(run())