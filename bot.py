import discord
import random
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import dateparser
import pytz

intents = discord.Intents.all()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

QueuesDict = {}             # Dictionary of queue_name string -> Queue() object
UsersInAllQueues = []       # List of user.id's

est = pytz.timezone('US/Eastern')


class Queue:
    def __init__(self, partyLeader, eventTime):
        self.queue = []                     # List of user.id's (Current queue)
        self.partyLeader = partyLeader;     # user.id
        self.eventTime = eventTime          # event time
        self.notified = False               # notification boolean
    
    def __del__(self):
        print(f'deleted')
    
    def display(self, bot):
        usernames = [bot.get_user(user_id).name for user_id in self.queue]
        return usernames

    async def send_notification(self, bot, ctx, queue_name):
        while datetime.now(est) < self.eventTime and not self.notified:
            await asyncio.sleep(1)  # Check every second
        
        if not self.notified:
            queue_obj = QueuesDict[queue_name]
            party_list = '\n'.join([f'{idx + 1}. <@{user}>' for idx, user in enumerate(queue_obj.queue)])
            await ctx.send(f'Queue time has been reached. \nEvent Time: **{QueuesDict[queue_name].eventTime}** \nParty Members in **{queue_name}**:\n{party_list}')
            self.notified = True  # Set the flag to avoid duplicate notifications

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

# You can only be present in one queue. DONE
# Only party leader can delete a queue. DONE
# bot.command: current (check what queue you're in) DONE
# Time parameters/display time DONE
# Notifications at time DONE
# Implement aliases for commands
# Feature: Change time (!time)
# Emoji reactions on queuelist


@bot.command(name='create', aliases=['c'], help='(!c <queue_name>) Create a queue.')
async def create_queue(ctx, queue_name=None):
    user = ctx.author
    print('Entered create')
    if user.id in UsersInAllQueues:
        await ctx.send(f'**ERROR!** User is already in a queue!')
    elif queue_name is None:
        await ctx.send(f'**ERROR!** Please enter the name of the queue after the command.')
    elif queue_name not in QueuesDict:
        await ctx.send(f'Queue **{queue_name}** is being created. Please provide the scheduled event time in the following format: **"11pm MM/DD"**. *(60s timeout)*')
        
        try:
            eventTime_str = await bot.wait_for('message', timeout=60.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            eventTime = dateparser.parse(eventTime_str.content)
            QueuesDict[queue_name] = Queue(user.id, eventTime)
            QueuesDict[queue_name].queue.append(user.id)
            UsersInAllQueues.append(user.id)
            await ctx.send(f'Queue **{queue_name}** has been successfully created. The event is scheduled for {eventTime}.')
            await ctx.send(f'{user.mention}, you have joined the queue.')
            await QueuesDict[queue_name].send_notification(bot, ctx, queue_name)
        except asyncio.TimeoutError:
            await ctx.send('Timeout. Please try again and provide the event time promptly.')
    
    else:
        await ctx.send(f'**ERROR!** Queue **{queue_name}** already exists!')


@bot.command(name='join', aliases=['j'], help='(!j <queue_name>) Join a queue.')
async def join_queue(ctx, queue_name=None):
    user = ctx.author
    print('Entered join')
    if user.id in UsersInAllQueues:
        await ctx.send(f'**ERROR!** User is already in a queue!')
    elif queue_name is None:
        await ctx.send(f'**ERROR!** Please enter the name of the queue after the command.')
    elif queue_name not in QueuesDict:
        await ctx.send('**ERROR!** The queue does not exist.')
    elif user.id not in QueuesDict[queue_name].queue:
        QueuesDict[queue_name].queue.append(user.id)
        UsersInAllQueues.append(user.id)
        await ctx.send(f'{user.mention}, you have joined the queue.')
    else:
        await ctx.send(f'**ERROR**! {user.mention}, you are already in the queue.')


@bot.command(name='leave', aliases=['l'], help='(!l) Leave the current queue.')
async def leave_queue(ctx):
    user = ctx.author
    isInQueue = False
    
    for obj in QueuesDict.values():
        if user.id in obj.queue:
            cur_queue_name = list(QueuesDict.keys())[list(QueuesDict.values()).index(obj)]
            isInQueue = True
    
    if isInQueue:
        QueuesDict[cur_queue_name].queue.remove(user.id)
        UsersInAllQueues.remove(user.id)
        await ctx.send(f'{user.mention}, you have left the queue.')
        if QueuesDict[cur_queue_name].partyLeader == user.id:
            if len(QueuesDict[cur_queue_name].queue) == 0:
                del QueuesDict[cur_queue_name]
                await ctx.send(f'Queue **{cur_queue_name}** has been deleted automatically due to no present members.')
            else:
                QueuesDict[cur_queue_name].partyLeader = QueuesDict[cur_queue_name].queue[0]
                await ctx.send(f'<@{QueuesDict[cur_queue_name].partyLeader}> is the new party leader.')
    else:
        await ctx.send(f'**ERROR**! {user.mention}, you are not in the queue.')


@bot.command(name='delete', aliases=['d'], help='(!d <queue_name>) Delete your queue.')
async def delete_queue(ctx, queue_name=None):
    user = ctx.author
    if queue_name is None:
        await ctx.send(f'**ERROR!** Please enter the name of the queue after the command.')
    elif queue_name not in QueuesDict:
        await ctx.send('**ERROR**! The queue does not exist.')
    else:
        if QueuesDict[queue_name].partyLeader != user.id:
            await ctx.send('**ERROR**! Only party leader can delete the queue.')
        else:
            curQueue = QueuesDict[queue_name].queue
            for userID in curQueue:
                UsersInAllQueues.remove(userID)
            del QueuesDict[queue_name]
            await ctx.send(f'Queue **{queue_name}** has been manually deleted.')
            
            
@bot.command(name='queue', aliases=['q'], help='(!q <queue_name>) Display a queue\'s members.')
async def display_party_members(ctx, queue_name=None):
    if queue_name is None:
        await ctx.send(f'**ERROR!** Please enter the name of the queue after the command.')
    elif queue_name not in QueuesDict:
        await ctx.send('**ERROR**! The queue does not exist.')
    else:
        queue_users = QueuesDict[queue_name].display(bot)
        party_list = '\n'.join([f'{idx + 1}. {user}' for idx, user in enumerate(queue_users)])
        await ctx.send(f'Party Leader: **{queue_users[0]}** \nEvent Time: **{QueuesDict[queue_name].eventTime}** \nParty Members in **{queue_name}**:\n{party_list}')


@bot.command(name='queuelist', aliases=['ql'], help='(!ql) Show\'s a list of all active queues.')
async def display_all_queues(ctx):
    if not QueuesDict:
        await ctx.send(f'There are currently no active queues. Create one with !create <queue_name>.')
    else:
        keys = QueuesDict.keys()
        queue_list = '\n'.join([f'{idx + 1}. **{key}**' for idx, key in enumerate(keys)])
        await ctx.send(f'Current Active Queues: \n{queue_list}')


@bot.command(name='current', aliases=['cur'], help='(!cur) Show\'s the current queue you\'re in.')
async def display_user_location(ctx):
    user = ctx.author
    isInQueue = False
    
    for obj in QueuesDict.values():
        if user.id in obj.queue:
            cur_queue_name = list(QueuesDict.keys())[list(QueuesDict.values()).index(obj)]
            isInQueue = True
    
    if isInQueue:
        await ctx.send(f'{user.mention}, you are currently in queue **{cur_queue_name}**.')
    else:
        await ctx.send('You are currently not in a queue. Use !join <queue> to join one!')


#@bot.command(name='debug', help='for dev')
#async def display_all_queues(ctx, queue_name):
#    for user in UsersInAllQueues:
#        print(f'UsersInAllQueues:\n')
#        print(f'{user} \n')

# Replace 'YOUR_BOT_TOKEN_HERE' with the token you obtained from the Discord Developer Portal
bot.run('')
