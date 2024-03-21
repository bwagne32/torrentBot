import discord
from discord.ext import tasks,commands
import qbittorrentapi
import datetime
import subprocess
import os
import signal
import sys


## qbittorrent ==========================================================================
conn_info = dict(
    host="127.0.0.1",
    port=8080,
    #username="admin", # enable auth connections from localhost in the ui
    #password="adminadmin",
)
qbt_client = qbittorrentapi.Client(**conn_info)

try: # login
    qbt_client.auth_log_in()
except qbittorrentapi.LoginFailed as e:
    print(e)

print(f"qBittorrent: {qbt_client.app.version}")
print(f"qBittorrent Web API: {qbt_client.app.web_api_version}")





## Discord ==============================================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
description = 'torrent bot'

bot = commands.Bot(command_prefix='?', description=description, intents=intents)

bot.remove_command('help')



@tasks.loop(minutes=5)
async def notify(): # Checks for completed torrents to notify in discord
    await bot.wait_until_ready()  # Wait until the bot is ready
    str = qbt_client.torrents_info(status_filter='completed', tag='')
    
    filtered_hashes = [torrent['hash'] for torrent in str]


    printStr = '```COMPLETED:\n'
    if (str):
        for i in range(len(str)):
            printStr += 'Location and Name:\t'
            printStr += (str[i]['content_path']) + '\n'
            
            if len(printStr) > 1000:
                printStr = '```COMPLETED:\n'
        printStr +='```'
 
        qbt_client.torrents_add_tags(tags='notify', torrent_hashes=filtered_hashes)
        await bot.get_channel(1164987769316192336).send(printStr)
    else:
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + '| No new downloads')
@bot.group(invoke_without_command=True)
async def help(ctx):
    em = discord.Embed(title="Help", description='Use !help <command> for extended information on a specific command.')
    em.add_field(name='Torrents Commands', value='`addtor`, `viewtorrents`, `checktor`, `yt`')
    em.add_field(name='PC Commands', value='`checkstorage`')
    await ctx.channel.send(embed=em)





@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('----------')
    #await notify()
    try:
        notify.start()
    except:
        print('failed to run notify')

async def is_owner(ctx):
    return ctx.author.id == 337680810054516736


@bot.command(aliases=['toradd', 'addtorrent', 'torrentadd', 'add'])
@commands.check(is_owner)
async def addtor(ctx, torHash, loc):
    print('Adding torrent with hash', torHash, 'to qBitTorrent downloads...')
    cli = qbt_client

    filePath = '/home/void/'
    match(filePath):
        case('ram'):
            filePath = filePath + 'ram/'
        case('show'):
            filePath = filePath + 'shows/'
        case('movie'):
            filePath = filePath + 'movies/'
        case('game'):
            filePath = filePath + '4tbBlue/games/'
        case(_):
            filePath = filePath + loc


    print(f'qBittorrent: {cli.app.version}')
    cli.torrents_add(urls=torHash, save_path=filePath)
    print('Added successfully.')
    await ctx.channel.send('Download begun. Use `?viewtorrents` to check the status.')    
    
    log = bot.get_channel(1194310407888834622)
    torStr = cli.torrents_info()
    torName = [torrent['name'] for torrent in torStr if torHash.lower() in torrent['magnet_uri'].lower()]
    await log.send('```' + str(ctx.author) + '```')
    try:
        await log.send("Torrent:" + "```" + torName[0] + "```")
    except:
        print("bruh")
    
    
@help.command()
async def addtor(ctx):
    em = discord.Embed(title='Add Torrent', description='Takes a torrent hash and save path from the user and starts downloading the contents to the host PC. <torHash> should be a valid torrent info hash, and <directory> should be a valid directory on the host PC.', color=ctx.author.color)
    em.add_field(name='**Syntax**', value='!addtor <torrent hash> <directory>')
    em.add_field(name='**Example directories**', value='`ram/`, `plex/shows/ (show)`, `plex/movies/ (movie)`, `4tbBlue/plex/games/ (games)`')
    em.add_field(name='**Aliases**', value='`!addtor`, `!addtorrent`, `!toradd`, `!torrentadd`')
    em.add_field(name='**Shortcuts**', value='`(/home/void/)`')
    await ctx.channel.send(embed=em)
    



@bot.command(aliases=['ct','checktorrent','check'])
@commands.check(is_owner)
async def checktor(ctx, name): # check status of torrent based on name
    cli = qbt_client
    torStr = cli.torrents_info()
    #filtered_torrents = [torrent['name'] for torrent in sendStr]
    filtered_torrents = [[torrent['name'] for torrent in torStr if name.lower() in torrent['name'].lower()], [torrent['progress'] for torrent in torStr if name.lower() in torrent['name'].lower()]]
    sendStr = [''] * 2 * len(filtered_torrents[0]) 
    for i in range(len(filtered_torrents[1])):
        filtered_torrents[1][i] = 100 * filtered_torrents[1][i]
        sendStr[2 * i] = filtered_torrents[0][i] + ': ' + str(filtered_torrents[1][i]) + '%' 
        sendStr[2 * i + 1] = '``````'

    
    await ctx.channel.send(f"```Progress for search: {name}``````{sendStr}```")
    #await ctx.channel.send(f"```Progress for search: {name}\n{filtered_torrents[0]}: {filtered_torrents[1]}%```")
@help.command()
async def checktor(ctx):
    em = discord.Embed(title='Check Torrent', description='Displays an enormous text wall of the torrent info dictionary, telling everything about a specified torrent. Hard to read, only to be used by those who know what they\'re looking at.')
    em.add_field(name='**Syntax**', value='?checktor <torrent filter name>')
    em.add_field(name='**Aliases**', value='`?checktor`, `?checktorrent`, `?ct`')
    await ctx.channel.send(embed=em)
    




@bot.command(aliases=['vt','torrentstatus','downloadstatus'])
@commands.check(is_owner)
async def viewtorrents(ctx, status):
    cli = qbt_client
    cStr = ''
    dStr = ''

    match status:
        case('a'):
            status = 'all'
        case('d'):
            status = 'down'
        case('u'):
            status = 'upload'
        case('c'):
            status = 'complete'

    match status:
        case('all'):
            completeStr = cli.torrents_info(status_filter='completed')
            downloadStr = cli.torrents_info(status_filter='downloading')
            uploadStr = cli.torrents_info(status_filter='uploading')
            await complete(ctx,completeStr)
            await up(ctx, downloadStr)
            await down(ctx, uploadStr)
            return
        case('up'):
            uploadStr = cli.torrents_info(status_filter='uploading')
            await up(ctx, downloadStr)
            return
        case('u'):
            uploadStr = cli.torrents_info(status_filter='uploading')
            await up(ctx, downloadStr)
            return
        case('down'):
            downloadStr = cli.torrents_info(status_filter='downloading')
            await down(ctx,downloadStr)
            return
        case('complete'):
            completeStr = cli.torrents_info(status_filter='completed')
            await complete(ctx,completeStr)
            return
    await ctx.channel.send('Invalid char. Use all/a, down/d, upload/up/u, complete/c')

@help.command()
async def viewtorrents(ctx):
    em = discord.Embed(title='View Torrents', description='View status of all current torrents.', color=ctx.author.color)
    em.add_field(name='**Aliases**', value='`!viewtorrents`, `!vt`, `!torrentstatus`, `!downloadstatus`')
    await ctx.channel.send(embed=em)



        


#sub functions ==========================================================================
async def complete(ctx,completeStr):
    cStr = '```COMPLETED:\n'
    if (not completeStr):
        sendStr += 'None.'
    for i in range(len(completeStr)):
        cStr += 'Location and Name:\t'
        cStr += (completeStr[i]['content_path']) + '\n\n'
        if len(cStr) > 1000:
            await ctx.channel.send(cStr + '```')
            cStr = '```COMPLETED:\n'
    cStr +='```'
    await ctx.channel.send(cStr)

async def up(ctx, uploadStr):
    str = '```UPLOADING:\n'
    if (not str):
        dStr += 'None.'
    for j in range(len(uploadStr)):
        str += 'Location and Name:\t'
        str += (uploadStr[j]['content_path']) + '\n\n'
        if len(str) > 1000:
            await ctx.channel.send(Str + '```')
            Str = '```DOWNLOADING:\n'

    str += '```'
    await ctx.channel.send(str)

async def down(ctx,downloadStr):
    dStr = '```DOWNLOADING:\n'
    if (not downloadStr):
        dStr += 'None.'
    for j in range(len(downloadStr)):
        dStr += 'Location and Name:\t'
        dStr += (downloadStr[j]['content_path']) + '\n\n'
        dStr += 'Progress Decimal Percent:\t'
        dStr += str((downloadStr[j]['progress'])) + '\n\n'
        if len(dStr) > 1000:
            await ctx.channel.send(dStr + '```')
            dStr = '```DOWNLOADING:\n'

    dStr += '```'
    await ctx.channel.send(dStr)


# Non torrent stuff ######################################################################3
@bot.command()
async def yt(ctx,URL): # Youtube downloader
    path = "/home/void/ram/"
    cmd = "yt-dlp -P " + path + " -o vid.webm "
    cmd = cmd + str(URL)
    try:
        subprocess.run(cmd,shell=True)
        try:
            await ctx.channel.send(file=discord.File(r'/home/void/ram/vid.webm'))
        except:
            await ctx.channel.send('Error in sending file (File is probably too large)')
    except:
        await ctx.channel.send('Invalid URL')
    subprocess.run('rm /home/void/ram/vid.webm',shell=True)
@help.command()
async def yt(ctx):
    em = discord.Embed(title='youtube dl', description='Download youtube video', color=ctx.author.color)
    await ctx.channel.send(embed=em)
        




@bot.command()
@commands.check(is_owner)
async def kys(ctx):
    try:
        # iterating through each instance of the process
        for line in os.popen("ps ax | grep " + "qbittorrent-nox" + " | grep -v grep"): 
            fields = line.split()
             
            # extracting Process ID from the output
            pid = fields[0] 
             
            # terminating process 
            os.kill(int(pid), signal.SIGKILL) 
        
        await ctx.channel.send('qbittorrent killed')
    except:
        await ctx.channel.send('Failed to close qbittorrent')
    
    await ctx.channel.send('Ending bot process')
    sys.exit(0)
    await ctx.channel.send('Failed to commit suicide')



TOKEN = open('torrentToken.txt','r')
bot.run(TOKEN.read())
