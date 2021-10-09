import os
import re
import asyncio
import time
import datetime

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
import requests

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER = os.getenv('DISCORD_GUILD')

client = commands.Bot(command_prefix='!')

# music queue. just using a list so people can move songs if they want
song_queue = []

# keep track of time left in song
TIME_STARTED = 0
CUR_SONG_DUR = 0
CUR_SONG_STR = ""

# streaming stuff
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True', 'cookiefile':'./youtube.com_cookies.txt'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_on_http_error 404,403 -reconnect_delay_max 5', 'options': '-vn'}

# When bot is up and connected to server(guild)
@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == SERVER:
            break
    print(
        f'{client.user} up in this bisshhh.\n'
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
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        return
    await voice_client.disconnect()

@client.command()
# ctx, *, search just returns all following args as a single str
async def play(ctx, *, search):
    global CUR_SONG_DUR
    global TIME_STARTED
    global CUR_SONG_STR
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        joined = await join(ctx)
        if not joined:
            return
        voice_client = ctx.message.guild.voice_client

    await ctx.send(f':musical_note: **Searching** :mag_right:`{search}`')

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
        try:
            info = ydl.extract_info(video_link, download=False)
        except DownloadError as e:
            if "confirm your age" in str(e):
                await ctx.send("UwU This song is too nyaughty fow me t-to h-handwe. Sowwy!!")
            else:
                await ctx.send("I absolutely bungled the download. Tell slippery dave.")
                print(f"Download error: {type(e)}")
            return
    song_duration = int(info['duration'])
    song_duration_str = f"{song_duration // 60}:{song_duration % 60:02d}"
    thumbnail_url = info['thumbnails'][0]['url']

    URL = info['formats'][0]['url']
    video_title = info['title']
    if voice_client.is_playing():
        song_dict = {
            "URL": URL,
            "duration_str": song_duration_str,
            "duration": song_duration,
            "title": video_title,
            "requestor": f"{ctx.author.display_name}",
        }
        song_queue.append(song_dict)
        embed = discord.Embed(
            title=video_title,
            url=f"https://www.youtube.com/watch?v={video_link}",
            )
        embed.set_author(
            name=f"{ctx.author.display_name} added to the queue",
            icon_url=ctx.author.avatar_url
            )
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(
            name="Song duration",
            value=song_duration_str,
            inline=True
            )
        time_left = CUR_SONG_DUR - int(time.time() - TIME_STARTED)
        time_until_play = sum(song["duration"] for song in song_queue) + time_left
        minutes, seconds = divmod(time_until_play, 60)
        hours, minutes = divmod(minutes, 60)
        if hours != 0:
            time_until_play = f"{hours}:{minutes:02d}:{seconds:02d}"
        # just minutes
        else:
            time_until_play = f"{minutes}:{seconds:02d}"
        embed.add_field(
            name="Estimated time until playing",
            value=time_until_play,
            inline=True
            )
        embed.add_field(
            name="Place in queue",
            value=len(song_queue),
            inline=False
            )
        await ctx.send(embed=embed)
    else:
        # Stream (no download)
        #await ctx.send(f'Playing [{video_title}](https://www.youtube.com/watch?v={video_link})')
        await ctx.send(f'**Playing** `{video_title}` now!')
        voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        voice_client.source = discord.PCMVolumeTransformer(voice_client.source, volume=0.25)
        CUR_SONG_DUR = song_duration
        TIME_STARTED = time.time()
        CUR_SONG_STR = f"[{video_title}](https://www.youtube.com/watch?v={video_link}) | `{song_duration_str} Requested by: {ctx.author.display_name}`"

def play_next(ctx):
    global CUR_SONG_DUR
    global TIME_STARTED
    global CUR_SONG_STR
    if len(song_queue) >= 1:
        song = song_queue.pop(0)
        URL = song["URL"]
        dur = song["duration"]
        voice_client = ctx.message.guild.voice_client
        CUR_SONG_DUR = dur
        TIME_STARTED = time.time()
        CUR_SONG_STR = f"[{song['title']}]({song['URL']}) | {song['duration_str']} Requested by: {song['requestor']}"
        voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))

@client.command()
async def skip(ctx):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        return
    voice_client.stop()

@client.command()
async def fs(ctx):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        return
    voice_client.skip()

@client.command()
async def move(ctx, src, dst):
    voice_client = ctx.message.guild.voice_client
    if not voice_client:
        return
    src = int(src)
    dst = int(dst)
    if src < 1 or src > len(song_queue) or dst < 1 or dst > len(song_queue) or src == dst:
        await ctx.send(f"You suck at math, check your numbers")
    song_queue.insert(dst-1, song_queue.pop(src-1))
    await ctx.send(f":white_check_mark: **Moved** `{song_queue[dst-1]['title']}` **to position {dst}**")


@client.command()
async def queue(ctx):
    guild = ctx.message.guild
    voice_client = guild.voice_client
    if not voice_client:
        print("EXITING")
        return

    embed = discord.Embed(
        name="\u200b",
        title=f"Queue for {guild}"
    )
    embed.add_field(
        name="__Now Playing:__",
        value=CUR_SONG_STR,
        inline=False
    )

    if not song_queue:
        await ctx.send(f"The queue is barren.")
        return

    # Next playing doesn't include current, start at 1
    for i, song in enumerate(song_queue, 1):
        embed.add_field(
            name="__Up Next:__" if i == 1 else "\u200b",
            value=f"`{i}) `[{song['title']}]({song['URL']}) | `{song['duration_str']} Requested by: {song['requestor']}`",
            inline=False
        )
    # TODO: clean this up, this is messy
    total_time = CUR_SONG_DUR - int(time.time() - TIME_STARTED)
    total_time += sum(song["duration"] for song in song_queue)
    minutes, seconds = divmod(total_time, 60)
    hours, minutes = divmod(minutes, 60)
    if hours != 0:
        total_time = f"{hours}:{minutes:02d}:{seconds:02d}"
    # just minutes
    else:
        total_time = f"{minutes}:{seconds:02d}"
    embed.add_field(
        name="\u200b",
        value=f"**{len(song_queue)} songs in queue | {total_time} total length**"
        )
    await ctx.send(embed=embed)


@client.command()
async def say(ctx, *, words):
    channel = ctx.channel
    print(str(channel))
    await ctx.send(words, tts=True)

client.run(TOKEN)