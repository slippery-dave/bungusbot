import os
import re
import asyncio
import time
import datetime
import json

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
# from dotenv import load_dotenv
# from youtube_dl import YoutubeDL
# from youtube_dl.utils import DownloadError
import yt_dlp
import requests

# load_dotenv()
with open('env.json') as infile:
    env_json = json.load(infile)

TOKEN = env_json['discord_token']
SERVER = env_json['discord_guild']

# TOKEN = os.getenv('DISCORD_TOKEN')
# SERVER = os.getenv('DISCORD_GUILD')

# streaming stuff
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True', 'cookiefile':'./new-cookies-2.txt'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_on_http_error 404,403 -reconnect_delay_max 5', 'options': '-vn'}

# Since everyone always complains that the volume is too high when joining,
# I'm just reducing it to a flat percentage of itself
VOLUME_REDUCER = 0.25

# Save our eardrums. And sanity. 
EAR_PROTECT = False
EAR_KEYWORDS = ['ear', 'rape', 'earrape', 'earape', 'earr', 'rrape']

# For keeping track of which channel to puppet to
PUPPET_CHANNEL = 0
PUPPET_CHANNEL_NAME = ''

class Music(commands.Cog):

    # TODO: these might need to be in ctor. Here, all instances of class share
    # music queue. just using a list so people can move songs if they want
    song_queue = []

    # keep track of time left in song
    TIME_STARTED = 0
    CUR_SONG_DUR = 0
    CUR_SONG_STR = ""

    def __init__(self, bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Bungus online...')
        print('Logged in as ', self.bot.user)
        print('ID:', self.bot.user.id)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):
        print(err)


    @commands.command()
    async def join(self, ctx):
        print('joining')
        destination = ctx.author.voice.channel
        # if ctx.voice_client is not None:
        #     await ctx.send('Join a voice channel first, idiot')
        #     return False

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(destination)
        
        # channel = ctx.message.author.voice.channel
        await destination.connect()

    @commands.command()
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            return
        await voice_client.disconnect()

    @commands.command()
    # ctx, *, search just returns all following args as a single str
    async def play(self, ctx, *, search):
        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            joined = await join(ctx)
            if not joined:
                return
            voice_client = ctx.message.guild.voice_client

        await ctx.send(f':musical_note: **Searching** :mag_right:`{search}`')

        search = search.replace(' ', '+')
        if EAR_PROTECT == True:
            search = ear_sanitize(search)
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

        # with YoutubeDL(YDL_OPTIONS) as ydl:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(video_link, download=False)
            except yt_dlp.DownloadError as e:
                if "confirm your age" in str(e):
                    await ctx.send("UwU This song is too nyaughty fow me t-to h-handwe. Sowwy!!")
                else:
                    await ctx.send("I absolutely bungled the download. Tell slippery dave.")
                    print(f"Download error: {type(e)}")
                return
        song_duration = int(info['duration'])
        song_duration_str = f"{song_duration // 60}:{song_duration % 60:02d}"
        thumbnail_url = info['thumbnails'][0]['url']

        # URL = info['formats'][0]['url']
        URL = info['url']
        video_title = info['title']
        if voice_client.is_playing():
            song_dict = {
                "URL": URL,
                "short_url": f"https://www.youtube.com/watch?v={video_link}",
                "duration_str": song_duration_str,
                "duration": song_duration,
                "title": video_title,
                "requestor": f"{ctx.author.display_name}",
            }
            self.song_queue.append(song_dict)
            embed = discord.Embed(
                title=video_title,
                url=song_dict['short_url'],
                )
            embed.set_author(
                name=f"{ctx.author.display_name} added to the queue",
                icon_url=ctx.author.avatar
                )
            embed.set_thumbnail(url=thumbnail_url)
            embed.add_field(
                name="Song duration",
                value=song_duration_str,
                inline=True
                )
            time_left = self.CUR_SONG_DUR - int(time.time() - self.TIME_STARTED)
            time_until_play = sum(song["duration"] for song in self.song_queue) + time_left
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
                value=len(self.song_queue),
                inline=False
                )
            await ctx.send(embed=embed)
        else:
            # Stream (no download)
            #await ctx.send(f'Playing [{video_title}](https://www.youtube.com/watch?v={video_link})')
            await ctx.send(f'**Playing** `{video_title}` now!')
            voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
            voice_client.source = discord.PCMVolumeTransformer(voice_client.source, volume=VOLUME_REDUCER)
            self.CUR_SONG_DUR = song_duration
            self.TIME_STARTED = time.time()
            self.CUR_SONG_STR = f"[{video_title}](https://www.youtube.com/watch?v={video_link}) | `{song_duration_str} Requested by: {ctx.author.display_name}`"

    def play_next(self, ctx):
        if len(self.song_queue) >= 1:
            song = self.song_queue.pop(0)
            URL = song["URL"]
            dur = song["duration"]
            voice_client = ctx.message.guild.voice_client
            self.CUR_SONG_DUR = dur
            self.TIME_STARTED = time.time()
            self.CUR_SONG_STR = f"[{song['title']}]({song['URL']}) | {song['duration_str']} Requested by: {song['requestor']}"
            voice_client.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
            voice_client.source = discord.PCMVolumeTransformer(voice_client.source, volume=VOLUME_REDUCER)

    # def ear_sanitize(search):
    #     new_search = ""
    #     for kw in EAR_KEYWORDS:
    #         new_search = return_str.replace(kw, '')
    #     return new_search

    @commands.command(aliases=['fs'])
    async def skip(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            return
        voice_client.stop()

    @commands.command()
    async def move(self, ctx, src, dst):
        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            return
        src = int(src)
        dst = int(dst)
        if src < 1 or src > len(self.song_queue) or dst < 1 or dst > len(self.song_queue) or src == dst:
            await ctx.send(f"You suck at math, check your numbers")
        self.song_queue.insert(dst-1, self.song_queue.pop(src-1))
        await ctx.send(f":white_check_mark: **Moved** `{self.song_queue[dst-1]['title']}` **to position {dst}**")

    @commands.command()
    async def remove(self, ctx, target):
        voice_client = ctx.message.guild.voice_client
        if not voice_client:
            return
        target = int(target)
        if target <= 0 or target > len(self.song_queue):
            await ctx.send(f"You're bad at math, try again")
        self.song_queue.pop(target-1)

    # @commands.command()
    # async def pause(ctx):
    #     voice_client = ctx.message.guild.voice_client
    #     voice_client.pause()


    # @commands.command()
    # async def resume(ctx):
    #     voice_client = ctx.message.guild.voice_client
    #     voice_client.resume()

    @commands.command()
    async def queue(self, ctx):
        guild = ctx.message.guild
        voice_client = guild.voice_client
        if not voice_client:
            print("EXITING")
            return

        embed = discord.Embed(
            # name="\u200b",
            title=f"Queue for {guild}"
        )
        embed.add_field(
            name="__Now Playing:__",
            value=self.CUR_SONG_STR,
            inline=False
        )

        if not self.song_queue:
            await ctx.send(f"The queue is barren.")
            return

        # Next playing doesn't include current, start at 1
        for i, song in enumerate(self.song_queue, 1):
            next_song_str = f"`{i})` [{song['title']}]({song['short_url']}) | `{song['duration_str']} Requested by: {song['requestor']}`"
            if len(next_song_str) >= 1024:
                next_song_str = next_song[:1023]
            embed.add_field(
                name="__Up Next:__" if i == 1 else "\u200b",
                value=next_song_str,
                inline=False
            )
        # TODO: clean this up, this is messy
        total_time = self.CUR_SONG_DUR - int(time.time() - self.TIME_STARTED)
        total_time += sum(song["duration"] for song in self.song_queue)
        minutes, seconds = divmod(total_time, 60)
        hours, minutes = divmod(minutes, 60)
        if hours != 0:
            total_time = f"{hours}:{minutes:02d}:{seconds:02d}"
        # just minutes
        else:
            total_time = f"{minutes}:{seconds:02d}"
        embed.add_field(
            name="\u200b",
            value=f"**{len(self.song_queue)} songs in queue | {total_time} total length**"
            )
        await ctx.channel.send(embed=embed)


    @commands.command()
    async def say(self, ctx, *, words):
        channel = ctx.channel
        print(str(channel))
        await ctx.send(words, tts=True)
   

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(
    command_prefix=commands.when_mentioned_or('!'),
    description='BIG BUNGUS BOY',
    intents=intents
    )

async def main():
    async with client:
        await client.add_cog(Music(client))
        await client.start(TOKEN)

asyncio.run(main())
