import os
import re
import asyncio

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
from youtube_dl import YoutubeDL
import requests

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER = os.getenv('DISCORD_GUILD')

client = commands.Bot(command_prefix='!')

# keep track of any active music players
players = {}

# music queue. just using a list so people can move songs if they want
queue = []

# streaming stuff
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == SERVER:
            break

    print(
        f'{client.user} up in this bicchhh.\n'
        f'\tserver: "{guild.name}" (id: {guild.id})'
    )

@client.command()
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send('Join a voice channel first, idiot')
        return False
    channel = ctx.message.author.voice.channel
    await channel.connect()
    return True

@client.command()
async def leave(ctx):
    guild = ctx.message.guild
    voice_client = guild.voice_client
    await voice_client.disconnect()

@client.command()
# ctx, *, search just returns all following args as a single str
async def play(ctx, *, search):
    guild = ctx.message.guild
    voice_client = guild.voice_client
    if not voice_client:
        joined = await join(ctx)
        if not joined:
            return
        voice_client = guild.voice_client

    await ctx.send(f':musical_note: **Searching** :mag_right:`{search}`')

    # if search.startswith('http') or search.startwith('www')
    search = search.replace(' ', '+')
    response = requests.get('https://www.youtube.com/results?search_query=' + search)
    video_ids = re.findall(r'watch\?v=(\S{11})', response.text)
    video_link = video_ids[0]

    # # Downloading file
    # YDL_OPTIONS = {
    #     'format': 'bestaudio',
    #     'postprocessors': [{
    #         'key': 'FFmpegExtractAudio',
    #         'preferredcodec': 'mp3',
    #         'preferredquality': '192',
    #     }],
    #     'outtmpl': 'song.%(ext)s',
    #     }
    # with YoutubeDL(YDL_OPTIONS) as ydl:
    #     ydl.download([search])
    # voice_client.play(FFmpegPCMAudio('song.mp3'))
    # voice_client.is_playing()

    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(video_link, download=False)
    URL = info['formats'][0]['url']
    video_title = info['title']
    if voice_client.is_playing():
        queue.append(URL)
        #await ctx.send(f'Added [{video_title}](https://www.youtube.com/watch?v={video_link})')
        embed = discord.Embed(
            title=video_title,
            url=f"https://www.youtube.com/watch?v={video_link}",
            )
        await ctx.send(embed=embed)
    else:
        # Stream (no download)
        #await ctx.send(f'Playing [{video_title}](https://www.youtube.com/watch?v={video_link})')
        await ctx.send(f'**Playing** `{video_title}` now!')
        voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))

def play_next(ctx):
    if len(queue) >= 1:
        URL = queue.pop(0)
        guild = ctx.message.guild
        voice_client = guild.voice_client
        voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))


@client.command()
async def stop(ctx):
    guild = ctx.message.guild
    voice_client = guild.voice_client
    if not voice_client:
        joined = await join(ctx)
        if not joined:
            return
        voice_client = guild.voice_client
    voice_client.stop()

# @client.event
# async def on_message(message):
#   if message.author == client.user:
#       return

#   if message.content.startswith('!'):
#       await message.channel.send(f'Someone said {message.content}')



# client = BungusClient()
client.run(TOKEN)