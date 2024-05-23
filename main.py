import os
import requests
from dotenv import load_dotenv
# from twitchio.ext import commands
from TwitchIO.twitchio.ext import commands
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
        with open(f"channels/{config['channel']}.jsonl", 'a') as channel_file:
            pass

        os.makedirs('channel', exist_ok=True)
        initial_channels = [
            os.path.splitext(channel_file)[0] for channel_file
            in os.listdir('channels')
        ]

        super().__init__(token=config['access_token'], prefix='!', initial_channels = initial_channels)
        self.channels = {}
        for channel in initial_channels:
            self.channels[channel] = StreamGuardBot(channel)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        
    async def event_message(self, message):
        if message.echo:
            return
    
        if message.content.startswith('!'):
            await self.handle_commands(message)
        else:
            message.content = '!_ask {question}'.format(question=message.content)
            await self.handle_commands(message)

    @commands.command(name='guard')
    async def add_channel(self, context: commands.Context, channel: str):
        if context.author.name != 'dennosity':
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
        channel = context.author.name

        # Ignore request if user did not previous call `!guard`
        if channel not in self.channels:
            return
        
        await context.send(f"Stream Guard Bot has left {channel}'s chat")
        await self.part_channels([channel])
        
        del self.channels[channel]
        os.remove(f'channels/{channel}.jsonl')

    @commands.command(name='addQA')
    async def add_qa(self, context: commands.Context, question: str, answer: str):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return

        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        stream_guard_bot.add_qa(question, answer)
        await context.send(f'Added {question} -> {answer} ')

    @commands.command(name='removeQA')
    async def remove_qa(self, context: commands.Context, index: int):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return
        
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        stream_guard_bot.remove_qa(index)

    @commands.command(name='listFAQ')
    async def list_faq(self, context: commands.Context):
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        faq = stream_guard_bot.list_faq()
        await context.send(faq)

    @commands.command(name='_ask')
    async def _ask(self, context: commands.Context, *, question: str):
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot._respond(question)
        
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

    @commands.command(name='setResponseThreshold')
    async def set_threhold(self, context: commands.Context, response_threshold: str):
        if not context.author.is_broadcaster and not context.author.is_mod:
            return
        
        response_threshold = float(response_threshold)
        channel = context.channel.name
        stream_guard_bot = self.channels[channel]
        response = stream_guard_bot.response_threshold = response_threshold

bot = Bot()
bot.run()