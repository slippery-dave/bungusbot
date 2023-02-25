## Installation

Just install requirements

```bash
pip install requirements.txt
```

Then update the .env file with the bots token (discord developer portal)

Also need to install ffmpeg. To see their official page, check [here](https://ffmpeg.org/).

On ubuntu (20.04 at least) it's as easy as:

```
sudo apt install ffmpeg

```

```text
DISCORD_TOKEN=<token>
DISCORD_GUILD=<whatever server/guild>
```

Setting up cookies (optional, for bypassing age-restricted videos)
- Sign in to youtube and get your cookies in a text file (e.g. I just used the chrome extension [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid?hl=en]))
- Make sure your cookiefile name matches the one specified in `YDL_OPTIONS` in bot.py

## Usage

Running is really easy:

```python
python bot.py
```

### Notes

Cookies were strangely difficult to get working. I found the solution by looking directly at the source files for youtube-dl (Specifically the [EMBEDDING YOUTUBE DL](https://github.com/ytdl-org/youtube-dl/blob/master/README.md]), which then pointed me to [YoutubeDL.py](https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L137-L312])). Took me a couple hours but finally figured it out with these gotchas:
- I haven't fully tested this but I suspect that when getting cookies, you must both be logged in *AND* have recently viewed an age restricted video *BEFORE* exporting your cookies. This will make sure you have the additional cookie so that youtube won't bother you again with the age restricted prompt that happens sometimes even when you're logged in.
- The command line option is just `--cookies` but the embedded (e.g. YoutubeDL in a python script) option is `cookiefile`, for some reason.
- When using TTS (e.g. ctx.send("...", tts=True)), you have to ensure that the bot has permissions to do so when adding it to a server.