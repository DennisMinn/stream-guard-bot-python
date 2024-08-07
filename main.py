import os
import requests
import asyncio
import textwrap
from dotenv import load_dotenv
from twitchio.ext import commands
from stream_guard import StreamGuardBot


load_dotenv(override=True)

config = {
    'client_id': os.environ['CLIENT_ID'],
    'client_secret': os.environ['CLIENT_SECRET'],
    'access_token': os.environ['ACCESS_TOKEN'],
    'refresh_token': os.environ['REFRESH_TOKEN'],
    'channel': os.environ['INITIAL_CHANNEL']
}


class Bot(commands.Bot):
    def __init__(self):
        os.makedirs('channels', exist_ok=True)

        initial_channels = [
            os.path.splitext(channel_file)[0] for channel_file
            in os.listdir('channels')
        ]

        super().__init__(token=config['access_token'], prefix='!', initial_channels=initial_channels)

        self.channels = {}
        for channel in initial_channels:
            self.channels[channel] = StreamGuardBot.from_pickle(f'channels/{channel}')

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

        # Refresh token after expiration period passes
        while True:
            expiration = await self.refresh_token()
            await asyncio.sleep((expiration - 1800))

    async def event_message(self, message):
        if message.echo:
            return

        if message.content.startswith('!'):
            await self.handle_commands(message)
        else:
            message.content = '!_ask {question}'.format(question=message.content)
            await self.handle_commands(message)

    async def refresh_token(self):
        url = 'https://id.twitch.tv/oauth2/token'
        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'grant_type': 'refresh_token',
            'refresh_token': config['refresh_token']
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=data, headers=headers)
        token = response.json()

        config['access_token'] = token['access_token']
        config['refresh_token'] = token['refresh_token']
        self._connection._token = token['access_token']

        return token['expires_in']

    @commands.command(name='guard')
    async def add_channel(self, context: commands.Context, channel: str):
        # Command can only be called in `stream_guard_bot`'s chat
        if context.channel.name != 'stream_guard_bot':
            return

        if channel in self.channels:
            await context.send(f'{channel} is already guarded!')
            return

        await context.send(f'{channel} is now guarded!')
        await self.join_channels([channel])
        # Stream Guard Bot Section
        self.channels[channel] = StreamGuardBot(channel)

    @commands.command(name='part')
    async def remove_channel(self, context: commands.Context):
        # Command can only be called in `stream_guard_bot`'s chat
        if context.channel.name != 'stream_guard_bot':
            return

        channel = context.author.name
        # Ignore request if user did not previous call `!guard`
        if channel not in self.channels:
            return

        await context.send(f"Stream Guard Bot has left {channel}'s chat")
        await self.part_channels([channel])

        del self.channels[channel]
        os.remove(f'channels/{channel}.jsonl')

    @commands.command(name='add')
    async def add_faq(self, context: commands.Context, question: str, answer: str):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot.add_faq(question, answer)

        await context.send(response)

    @commands.command(name='remove')
    async def remove_faq(self, context: commands.Context, index: int):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot.remove_faq(index - 1)

        await context.send(response)

    @commands.command(name='update')
    async def update_faq(self, context: commands.Context, index: int, answer: str):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot.remove_faq(index - 1)

        await context.send(response)

    @commands.command(name='faq')
    async def list_faq(self, context: commands.Context):
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        faq = stream_guard_bot.list_faq()

        chunks = textwrap.wrap(faq, 500)
        for chunk in chunks:
            await context.send(chunk)

    @commands.command(name='_ask')
    async def retrieval_ask(self, context: commands.Context, *, question: str):
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]

        response = stream_guard_bot.retrieval_respond(question, qa_index)
        if response == '':
            return

        await context.reply(response)

    @commands.command(name='ask')
    async def ask(self, context: commands.Context, *, question: str):
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot.respond(question)
        
        if response == '':
            return
        
        await context.reply(response)

    @commands.command(name='setThreshold')
    async def set_threhold(self, context: commands.Context, response_threshold: str):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        response_threshold = float(response_threshold)
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        stream_guard_bot.response_threshold = response_threshold

        await context.send(f'Response Threshold set to {response_threshold}')

    @commands.command(name='enableAsk')
    async def enableAsk(self, context: commands.Context):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        stream_guard_bot.toggle_ask_command = True

        await context.send('!ask enabled')

    @commands.command(name='disableAsk')
    async def disableAsk(self, context: commands.Context):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        stream_guard_bot.toggle_ask_command = False

        await context.send('!ask disabled')


bot = Bot()
bot.run()
