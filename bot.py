import sys
import discord
from discord.ext import commands
import whisper
import wave
import io
import os
import asyncio
from datetime import datetime

from discord.ext.voice_recv import VoiceRecvClient, AudioSink, VoiceData

TRANSCRIPTION_INTERVAL = 4
PAUSE_THRESHOLD = 5

ANSI_COLORS = [
    "31", # Red
    "32", # Green
    "34", # Blue
    "35", # Magenta
    "36", # Cyan
    "1;31", # Bright Red
    "1;32", # Bright Green
    "1;33", # Bright Yellow
    "1;34", # Bright Blue
    "1;35", # Bright Magenta
    "1;36", # Bright Cyan
]

if len(sys.argv) < 2:
    print("Error: Bot token not provided. Usage: python bot.py <YOUR_BOT_TOKEN>")
    sys.exit(1)

TOKEN = sys.argv[1]

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
voice_clients = {}

try:
    print("Loading Whisper model...")
    whisper_model = whisper.load_model("base")
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    sys.exit(1)

class LiveTranscriptionSink(AudioSink):
    def __init__(self, ctx: commands.Context, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.ctx = ctx
        self.loop = loop
        self.user_audio_data = {}
        self.user_transcriptions = {}
        self.user_last_spoken_time = {}
        self.user_colors = {}

        self._active = True
        self.transcription_message = None
        self._task = None

    def start(self):
        self._task = self.loop.create_task(self._transcribe_loop())

    def wants_opus(self) -> bool:
        return False

    def write(self, user: discord.User | discord.Member | None, data: VoiceData):
        if user and data.pcm and self._active:
            if user.id not in self.user_audio_data:
                self.user_audio_data[user.id] = io.BytesIO()
            self.user_audio_data[user.id].write(data.pcm)
            self.user_last_spoken_time[user.id] = datetime.now()

    def cleanup(self):
        self._active = False
        if self._task:
            self._task.cancel()
        asyncio.run_coroutine_threadsafe(self.update_embed(final=True), self.loop)

    async def _transcribe_loop(self):
        while self._active:
            await asyncio.sleep(TRANSCRIPTION_INTERVAL)
            
            audio_to_process = self.user_audio_data.copy()
            for user_id in self.user_audio_data:
                self.user_audio_data[user_id] = io.BytesIO()

            for user_id, pcm_buffer in audio_to_process.items():
                if pcm_buffer.getbuffer().nbytes == 0:
                    continue

                pcm_buffer.seek(0)
                temp_file_path = f"temp_audio_{user_id}.wav"
                
                with wave.open(temp_file_path, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(48000)
                    wf.writeframes(pcm_buffer.read())

                try:
                    result = whisper_model.transcribe(temp_file_path, fp16=False)
                    text = result["text"].strip()
                    if text:
                        self.append_transcription(user_id, text)
                except Exception as e:
                    print(f"Error during transcription for user {user_id}: {e}")
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            
            await self.update_embed()

    def append_transcription(self, user_id: int, text: str):
        now = datetime.now()
        last_spoke = self.user_last_spoken_time.get(user_id, datetime.min)
        is_new_paragraph = (now - last_spoke).total_seconds() > PAUSE_THRESHOLD or user_id not in self.user_transcriptions

        current_transcription = self.user_transcriptions.get(user_id, "")
        if current_transcription and not current_transcription.endswith(' '):
            self.user_transcriptions[user_id] += ' '

        formatted_text = text.replace('. ', '.\n').replace('? ', '?\n').replace('! ', '!\n')

        if is_new_paragraph:
            timestamp = now.strftime('%H:%M:%S')
            separator = "\n\n" if current_transcription else ""
            self.user_transcriptions[user_id] = current_transcription + separator + f"`[{timestamp}]` {formatted_text}"
        else:
            self.user_transcriptions[user_id] += formatted_text

    async def update_embed(self, final=False):
        if not self.user_transcriptions:
            description = "Listening..."
        else:
            description_parts = []
            for user_id, text in self.user_transcriptions.items():
                if user_id not in self.user_colors:
                    color_index = len(self.user_colors) % len(ANSI_COLORS)
                    self.user_colors[user_id] = ANSI_COLORS[color_index]
                
                user_color_code = self.user_colors[user_id]

                try:
                    user = await self.ctx.bot.fetch_user(user_id)
                    display_name = user.display_name
                except discord.NotFound:
                    display_name = f"User ID: {user_id}"

                colored_header = f"\u001b[{user_color_code}m{display_name}\u001b[0m"
                colored_text = text.replace("`[", f"\u001b[33m[").replace("]`", "]\u001b[0m")
                
                description_parts.append(f"{colored_header}\n{colored_text}")

            description = f"```ansi\n" + "\n\n".join(description_parts) + "\n```"

        embed = discord.Embed(
            title="Live Transcription" if not final else "Transcription Complete",
            description=description,
            color=discord.Color.red() if not final else discord.Color.green()
        )

        if not self.transcription_message:
            self.transcription_message = await self.ctx.send(embed=embed)
        else:
            try:
                await self.transcription_message.edit(embed=embed)
            except discord.NotFound:
                self.transcription_message = await self.ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='join')
async def join(ctx: commands.Context):
    if not ctx.author.voice:
        await ctx.send("You must be in a voice channel to use this command.")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        voice_client = await channel.connect(cls=VoiceRecvClient)
        voice_clients[ctx.guild.id] = voice_client
    sink = LiveTranscriptionSink(ctx, bot.loop)
    voice_clients[ctx.guild.id].listen(sink)
    sink.start()
    await ctx.send(f"Joined {channel.name} and started live transcription.", delete_after=10)

@bot.command(name='leave')
async def leave(ctx: commands.Context):
    voice_client = voice_clients.get(ctx.guild.id)
    if not voice_client or not voice_client.is_connected():
        await ctx.send("I am not currently in a voice channel.")
        return
    voice_client.stop_listening()
    await voice_client.disconnect()
    del voice_clients[ctx.guild.id]
    await ctx.send("Left the voice channel.", delete_after=10)

bot.run(TOKEN)