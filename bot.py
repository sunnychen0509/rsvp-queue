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

class Queue:
    def __init__(self, partyLeader, eventTime):
        self.queue = []                     # List of user.id's (Current queue)
        self.fill = []                      # List of user.id's (Fill queue)
        self.partyLeader = partyLeader;     # user.id
        self.eventTime = eventTime          # event time
    
    def __del__(self):
        print(f'deleted')
    
    def display(self, bot):
        usernames = [bot.get_user(user_id).name for user_id in self.queue]
        return usernames
        
    async def send_notification(self, bot, ctx, queue_name):
        est = pytz.timezone('US/Eastern')
        eventTime_est = self.eventTime.astimezone(est)
        time_difference = eventTime_est - datetime.now(est)
        time_difference_in_seconds = time_difference.total_seconds()
        print(f'time_difference_in_seconds: {time_difference_in_seconds}')
        await asyncio.sleep(time_difference_in_seconds)
        queue_obj = QueuesDict[queue_name]
        party_list = '\n'.join([f'{idx + 1}. <@{user}>' for idx, user in enumerate(queue_obj.queue)])
        await ctx.send(f'Queue time has been reached. \nEvent Time: **{QueuesDict[queue_name].eventTime}** \nParty Members in **{queue_name}**:\n{party_list}')

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


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Process the message or add your commands here
    if (message.content.startswith('rudy') or
        message.content.startswith('Rudy') or
        message.content.startswith('RUDY')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('you are HORRENDOUS.')
        elif (r == 2):
            await message.channel.send('My friends flaked for the eighth time this week. Val?')
        elif (r == 3):
            await message.channel.send('Trust, blue looks good on me.')
        elif (r == 4):
            await message.channel.send('Why do programmers prefer dark mode? Because light attracts bugs. Sorry.')
        elif (r == 5):
            await message.channel.send('Most successful dropout can\'t even lie :sunglasses:')

    if (message.content.startswith('jav') or
        message.content.startswith('Jav') or
        message.content.startswith('JAV')):
        r = random.randint(1, 6)
        if (r == 1):
            await message.channel.send('MEOW')
        elif (r == 2):
            await message.channel.send('WOOF')
        elif (r == 3):
            await message.channel.send('YIPPEE')
        elif (r == 4):
            await message.channel.send('uwu you\'re so warm')
        elif (r == 5):
            await message.channel.send('*huff* Hold on, lemme catch my breath...')
        elif (r == 6):
            await message.channel.send('*huff* Hold on, lemme catch my breath...')

    if (message.content.startswith('aadi') or
        message.content.startswith('Aadi') or
        message.content.startswith('AADI')):
        r = random.randint(1, 6)
        if (r == 1):
            await message.channel.send('Watch your mouth around the greatest individual to ever tread on Mother Earth.')
        elif (r == 2):
            await message.channel.send('YOU GUYS ARE SO BAD AT VALORANT :rage:')
        elif (r == 3):
            await message.channel.send('Kodiak still owes me for rent... in my head.')
        elif (r == 4):
            await message.channel.send('I\'m not hardstuck, I swear.')
        elif (r == 5):
            await message.channel.send('https://preview.redd.it/k4dncypvfx191.png?width=1920&format=png&auto=webp&s=cdf82e1f80b40371850fe668703becc23d42c905')
        elif (r == 6):
            await message.channel.send('*Has $8000*. Can someone drop me this? https://liquipedia.net/commons/images/a/a7/Shorty_dbs-20_VALORANT.png')
           
    if (message.content.startswith('ant') or
        message.content.startswith('Ant') or
        message.content.startswith('ANT')):
        r = random.randint(1, 6)
        if (r == 1):
            await message.channel.send('https://www.youtube.com/watch?v=lwXm0odZ1ls')
        elif (r == 2):
            await message.channel.send('Ba Yi Fu TOUUUU Xia Lai!')
        elif (r == 3):
            await message.channel.send('girlfriend buff, tiff diff')
        elif (r == 4):
            await message.channel.send('I\'m not saying I\'m gay, but $20 is $20.')
        elif (r == 5):
            await message.channel.send('https://cdn.discordapp.com/attachments/871950306634772520/1190414989643743363/IMG_8231.jpg?ex=65a1b75a&is=658f425a&hm=b3884f741ab196f8752c20c7ec95c22cbdfac982cc4da67b01ebe14d083f42f1&')
        elif (r == 6):
            await message.channel.send('I may have a skill issue, but it could be worse. Take Rudy for example; that\'s a SKIN issue.')
    
    if (message.content.startswith('sunny') or
        message.content.startswith('Sunny') or
        message.content.startswith('SUNNY')):
        r = random.randint(1, 6)
        if (r == 1):
            await message.channel.send('THAT\'S FUCKING ON HIS HEAD!!')
        elif (r == 2):
            await message.channel.send('Every girl needs a guy who can stream 270bpm in osu. :sunglasses:')
        elif (r == 3):
            await message.channel.send('There is a higher probability of being struck twice by lightning at the same place at the same time than Sunny quitting val for more than three days. Extra points if he prefaces it with \"I\'m quitting for good.\"')
        elif (r == 4):
            await message.channel.send('My sweet, sweet baby boy Abdul, come over here and pull your pants dow-')
        elif (r == 5):
            await message.channel.send('*Leaves five stack*')
        elif (r == 6):
            await message.channel.send('Genuine contender for worst dolphin laugh.')
    
    if (message.content.startswith('usuf') or
        message.content.startswith('Usuf') or
        message.content.startswith('USUF') or
        message.content.startswith('yousuf') or
        message.content.startswith('Yousuf') or
        message.content.startswith('YOUSUF')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('https://medal.tv/games/valorant/clips/MSyRO5BQauKK0/d1337Ouh3eC4?invite=cr-MSxqRWosMjE5NTYzODQs\'')

        elif (r == 2):
            await message.channel.send('Nice one Aadi. Nice one buddy.')
        elif (r == 3):
            await message.channel.send('yoooooOOOOOOOOOO~ :man_with_chinese_cap:')
        elif (r == 4):
            await message.channel.send('Bro, bro, GUYS, I\'m alone on site fighting a war and no one breaks my dart, the drone, the reyna eye, the skye dog, and this Jett is just updrafting top gen with two smokes and everyone else is still rotating when I called five man A as soon as the round started. And bro, Aadi, why did you buy an op if you aren\'t gonna kill someone with it? All good, nice try everyone :).')
        elif (r == 5):
            await message.channel.send('https://imgflip.com/i/8aunti')
    
    if (message.content.startswith('jason') or
        message.content.startswith('Jason') or
        message.content.startswith('JASON') or
        message.content.startswith('chen') or
        message.content.startswith('Chen') or
        message.content.startswith('CHEN')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('Are you the greatest of all time? No? Then why are you talking in the presence of him? That\'s what I thought.')
        elif (r == 2):
            await message.channel.send('This guy is literally terrible.')
        elif (r == 3):
            await message.channel.send('A little bit TOOOO easy for me! Let me get some penguin head real quick *gawk gawk*')
        elif (r == 4):
            await message.channel.send('https://media1.tenor.com/m/rUpNz5ljeW8AAAAC/mr-popo-popo.gif @Rudy')
        elif (r == 5):
            await message.channel.send('Single-handedly ended racism by... not sure, might wanna ask him yourself.')
    
    if (message.content.startswith('eddy') or
        message.content.startswith('Eddy') or
        message.content.startswith('EDDY') or
        message.content.startswith('eddie') or
        message.content.startswith('Eddie') or
        message.content.startswith('EDDIE')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('*Manic Laughter Ensues*')
        elif (r == 2):
            await message.channel.send('BRO YOU ARE ILLEGAL')
        elif (r == 3):
            await message.channel.send('Yellow looks good on me... in multiple contexts.')
        elif (r == 4):
            await message.channel.send('https://www.youtube.com/watch?v=Dwaco8m_WRo')
        elif (r == 5):
            await message.channel.send('https://media.makeameme.org/created/look-at-you-bbf452f60c.jpg')
            
    if (message.content.startswith('haley') or
        message.content.startswith('Haley') or
        message.content.startswith('HALEY')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('Haley explaning why the new Sims 4 $150 DLC for a lamp and nightstand was a reasonable purchase: https://media.tenor.com/6RvyvMjx3XMAAAAM/he-is-speaking-guy-explaining-with-a-whiteboard.gif')
        elif (r == 2):
            await message.channel.send('*dies* THIS MOTHERFUCKING WHOR-')
        elif (r == 3):
            await message.channel.send('**Sunny**: *communicates with an unknown form of motionless telepathy.* **Haley**: *Drops skin.*')
        elif (r == 4):
            await message.channel.send('Holds the record for most number of anxiety inputs during a 1v1 situation.')
        elif (r == 5):
            await message.channel.send('OH MY GOD ETHAN GOT MARRIED POG')
        
    if (message.content.startswith('rylee') or
        message.content.startswith('Rylee') or
        message.content.startswith('RYLEE')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('*Plants the bomb, gets seven ult points from one round, wins a 1v5 clutch, literally rolls the enemy so hard and ruins their morale so terribly they ff next round...* GUYS I\'M SORRY')
        elif (r == 2):
            await message.channel.send('*dies* THIS FUCKING BITC-')
        elif (r == 3):
            await message.channel.send('It\'s always a pleasure. :slight_smile:')
        elif (r == 4):
            await message.channel.send('**Rylee**: I don\'t know why everyone says I\'m so old, I\'m only 21. **Rudy**: In dog years LOL.')
        elif (r == 5):
            await message.channel.send('Hm... I wonder who I\'m playing in the five stack today. https://liquipedia.net/commons/images/thumb/4/41/Skye_Artwork.png/600px-Skye_Artwork.png')

    if (message.content.startswith('abhi') or
        message.content.startswith('Abhi') or
        message.content.startswith('ABHI') or
        message.content.startswith('funky') or
        message.content.startswith('Funky') or
        message.content.startswith('FUNKY') or
        message.content.startswith('fucky') or
        message.content.startswith('Fucky') or
        message.content.startswith('FUCKY')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('*spray* You can get some head, *spray* and YOU can get some head, *spray* and YOU c-')
        elif (r == 2):
            await message.channel.send('Wait I can\'t hear you. What are you talking about? A 9-to-5? You mean the score of the val game I\'m in right now?')
        elif (r == 3):
            await message.channel.send('https://cdn.discordapp.com/attachments/871950306634772520/1147721057814462555/Immo-2-peak-sunny-pt.-2.mp4?ex=659a0d87&is=65879887&hm=223d78defea2f3a6e8f4276067ec923cc644d42fa997e7a56a587af20a262394&')
        elif (r == 4):
            await message.channel.send('What\'s up? Who\'s talking trash? Tell them to talk a little louder, it\'s hard to hear through this fat wad of cash blocking my ears right now, and the noise of their mom slurping me')
        elif (r == 5):
            await message.channel.send('Some people call me fuckyhippo. Why? It\'s quite simple really. I really want to fuck a hipp-')
        
    if (message.content.startswith('blade') or
        message.content.startswith('Blade') or
        message.content.startswith('BLADE') or
        message.content.startswith('abdul') or
        message.content.startswith('Abdul') or
        message.content.startswith('ABDUL')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('KYS (keep yourself safe :slight_smile: :thumbsup:)')
        elif (r == 2):
            await message.channel.send('I swear I\'m not depressed, it\'s just the mic.')
        elif (r == 3):
            await message.channel.send('duo? duo? duo? https://media.giphy.com/media/kLk1Qa8mrYdQA/giphy.gif')
        elif (r == 4):
            await message.channel.send('All I\'m saying is, if the opposing team has any EU players, the Geneva Convention did not exist in my books.')
        elif (r == 5):
            await message.channel.send('Should I put the period after K in KYS, or after the Y in KYS to not get banned... hmm... ')
    
    if (message.content.startswith('steve') or
        message.content.startswith('Steve') or
        message.content.startswith('STEVE') or
        message.content.startswith('stephen') or
        message.content.startswith('Stephen') or
        message.content.startswith('STEPHEN')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('Out of the two contending marshal players in today\'s competition, Stephen placed 3rd overall. Well done Stephen!')
        elif (r == 2):
            await message.channel.send('I only have two moods. 1) Game, 2) Jess.')
        elif (r == 3):
            await message.channel.send('ERM, YACTUALLY... https://media1.tenor.com/m/AlvyE4oRj24AAAAd/nerd-nerd-emoji.gif')
        elif (r == 4):
            await message.channel.send('https://miro.medium.com/v2/resize:fit:1400/format:webp/0*Alragq_xrc6Lms6p.jpg')
        elif (r == 5):
            await message.channel.send('Hear me out, I swear it\'s just an eevee with a hat on, I\'m not a furr-')
    
    if (message.content.startswith('hamza') or
        message.content.startswith('Hamza') or
        message.content.startswith('HAMZA') or
        message.content.startswith('penguin') or
        message.content.startswith('Penguin') or
        message.content.startswith('PENGUIN')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('This message pop-up will be more punctual than Hamza will be at literally anything else. Hamza will probably be late to his friend\'s funeral.')
        elif (r == 2):
            await message.channel.send('Guys')
        elif (r == 3):
            await message.channel.send('https://i.pinimg.com/originals/fc/3f/2d/fc3f2dcd91bbc4e82dd25da2da9fb8ca.jpg')
        elif (r == 4):
            await message.channel.send('*inhales*, I\'m gold 3... *Instant demotes to iron 1 after how the atrocities after this self pep-talk played out.*')
        elif (r == 5):
            await message.channel.send('Sorry guys, I got a meeting at 4pm, 6pm, 7pm, and 2:41am, I\'ll be back on later, promise. https://i.ytimg.com/vi/U7CZcd-UYmU/maxresdefault.jpg')
    
    if (message.content.startswith('jay') or
        message.content.startswith('Jay') or
        message.content.startswith('JAY')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('COME OVER HERE AND KISS ME ON MY HOT MOUTH. I\'M FEELING... ROMANTICAL.')
        elif (r == 2):
            await message.channel.send('Roses are red, pickles are green, I like your legs, and what\'s in between.')
        elif (r == 3):
            await message.channel.send('This... this is perfection. https://www.zleague.gg/theportal/wp-content/uploads/2023/05/Marshal-Valorant-weapon-guide-title-card-aspect-ratio-2-1.png')
        elif (r == 4):
            await message.channel.send('https://cdn.discordapp.com/attachments/1190392821870502041/1190738966266269759/IMG_9010.png?ex=65a2e514&is=65907014&hm=10d22ec7c30a0d9bf44d19ff71d44e66b30b75a50fc03ed2c28ab24cf1b37a8f&')
        elif (r == 5):
            await message.channel.send('I\'m not saying I\'m gay but... $20 is $20. Hell, I\'ll double down. I\'d PAY THAT $20 TO SUCK SOME D-')
    
    if (message.content.startswith('manav') or
        message.content.startswith('Manav') or
        message.content.startswith('MANAV') or
        message.content.startswith('blank') or
        message.content.startswith('Blank') or
        message.content.startswith('BLANK')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('**Aadi/Yousuf**: *Give a whole essay response as to why Manav misplayed a postplant terribly*. **Manav**: *Nods his head irl*')
        elif (r == 2):
            await message.channel.send('Do any of you guys know the feeling of sitting on a camera for three hours on B while the opposing team is 5-man rushing A? No? I\'ll have you know, it\'s some rivetting gameplay, let me show yo- oh no Aadi and Yousuf are yelling at me again, one second...')
        elif (r == 3):
            await message.channel.send('They call me the master-baiter.')
        elif (r == 4):
            await message.channel.send('Is it possible to get negative first bloods on a duelist? Can I try? Why is there only one person in the five stack...')
        elif (r == 5):
            await message.channel.send('My duo Aadi still hasn\'t paid me for last week\'s boost. *Sigh*')
            
    if (message.content.startswith('sunjay') or
        message.content.startswith('Sunjay') or
        message.content.startswith('SUNJAY') or
        message.content.startswith('sungay') or
        message.content.startswith('Sungay') or
        message.content.startswith('SUNGAY')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('Why do people say I only play one agent? That\'s straight cap. I play Chamber and Reyna! That\'s two! Just like the act I got Radiant in...')
        elif (r == 2):
            await message.channel.send('Some people call me sunjay, some people call be sungay, but when will that special someone call me sunbae? :sad_orange:')
        elif (r == 3):
            await message.channel.send('I wish I could hear what you\'re saying right now, but unfortunately, my headphones are off... for the fifth time this game.')
        elif (r == 4):
            await message.channel.send('Bro, I\'m not 5\'11, I\'m six feet tall, what\'re you on about? Oh, wait... you were talking about my KDA? Look, Jett is hard to get kills on.')
        elif (r == 5):
            await message.channel.send('Can\'t play val without that zaza pack yahearddddd')
            
    if (message.content.startswith('nikhil') or
        message.content.startswith('Nikhil') or
        message.content.startswith('NIKHIL') or
        message.content.startswith('niki') or
        message.content.startswith('Niki') or
        message.content.startswith('NIKI')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('I don\'t like being called nikipoo. I swear I don\'t. Eh, actually, lowkey...')
        elif (r == 2):
            await message.channel.send('**Blade**: How\'s your day been? **Nikhil**: BRO TODAY AT DSP-')
        elif (r == 3):
            await message.channel.send('My fellow businessmen, Rho Tau Chapter of Delta Sigma Pi was founded here at Rutgers University-New Brunswick on October 1st, 2011 which started the journey of establishing a premier professional business fraternity. Our founders worked tirelessly and were determined to leave a legacy of a fraternity that would have distinguished members for years to come, and here we are today. With over 60 active brothers and an alumni network of 200+ engaged members of diverse skills, backgrounds, and perspectives, we are committed to three fundamental principles. The three principles are professional development, philanthropy, and brotherhood for life. Ever since I decided to step out of my comfort zone and pursued joining this organization, these three pillars have been made clear to me as crucial aspects of this fraternity that we all value as a collective. Our active and alumni brothers have been extremely successful professionally throughout many industries as they have continuously been able to secure internships and full-time offers at firms like SpaceX, Amazon, Unilever, Morgan Stanley, Accenture, Deloitte, and many more. Our brothers have access to a variety of fields through networking, professional workshops, recruiting events, and career panels. As President of Rho Tau Chapter, I welcome you to our brotherhood.')
        elif (r == 4):
            await message.channel.send('Sunny\'s coaching was incredible! In a week, I heeded his advice and went from ascendant 2 to diamond 3! Sunny never fails to fail me!')
        elif (r == 5):
            await message.channel.send('I wonder what I\'m playing in premier this week... https://images.contentstack.io/v3/assets/bltb6530b271fddd0b1/blt5599d0d810824279/6036ca30ce4a0d12c3ec1dfa/V_AGENTS_587x900_Astra.png')
            
    if (message.content.startswith('justin') or
        message.content.startswith('Justin') or
        message.content.startswith('JUSTIN') or
        message.content.startswith('zyk') or
        message.content.startswith('Zyk') or
        message.content.startswith('ZYK')):
        r = random.randint(1, 5)
        if (r == 1):
            await message.channel.send('Roses are red, I\'m sipping coffee, If I stay muted the whole call, no one shall see me.')
        elif (r == 2):
            await message.channel.send('Justin, when a meeting is called in Among Us. https://www.chanty.com/blog/wp-content/uploads/2021/07/Screenshot-2021-07-22-at-11.48.01.jpg')
        elif (r == 3):
            await message.channel.send('*silence*, *crickets chirping*')
        elif (r == 4):
            await message.channel.send('My status changes every day, and my profile picture changes every hour. Why? Must refurbish my disguise.')
        elif (r == 5):
            await message.channel.send('If I took a shot for every minute Justin was unmuted in a call, I\'d have the prerequisites for an alcohol anonymous counselor.')
    
    # Allow other event handlers to process the message
    await bot.process_commands(message)

# Additional commands can be added here using the @bot.command decorator

# Replace 'YOUR_BOT_TOKEN_HERE' with the token you obtained from the Discord Developer Portal
bot.run('MTE5MDM5MTU3MDQ4NzMzMjkyNQ.G8Ofvl.hmHRbwj6ZghmdwI33D5NNkvBK8JmvmtGkOOczw')
