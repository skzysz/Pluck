import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import threading
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# --- НАСТРОЙКИ ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv('DISCORD_TOKEN')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"log_channel_id": ""}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- DISCORD БОТ ---
class LoggerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

bot = LoggerBot()

async def get_log_channel(guild):
    config = load_config()
    cid = config.get("log_channel_id")
    if cid and str(cid).isdigit():
        channel = guild.get_channel(int(cid))
        if isinstance(channel, discord.TextChannel):
            return channel
    return None

@bot.event
async def on_ready():
    print(f'[БОТ] {bot.user} запущен!')

# --- ПРОВЕРКА, ВИДИТ ЛИ БОТ СООБЩЕНИЯ ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    print(f"[DEBUG] Бот видит сообщение: '{message.content}' от {message.author.name}")

# --- ЛОГ ИЗМЕНЕННЫХ СООБЩЕНИЙ ---
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    print(f"[БОТ] Обнаружено измененное сообщение от {before.author.name}")

    channel = await get_log_channel(before.guild)
    if not channel: return

    embed = discord.Embed(title="✏️ Сообщение изменено", color=discord.Color.orange(), url=after.jump_url)
    embed.add_field(name="Автор", value=before.author.mention, inline=True)
    embed.add_field(name="Канал", value=before.channel.mention, inline=True)
    embed.add_field(name="Было", value=before.content[:1024] or "*Пусто*", inline=False)
    embed.add_field(name="Стало", value=after.content[:1024] or "*Пусто*", inline=False)
    await channel.send(embed=embed)

# --- ЛОГ УДАЛЕННЫХ СООБЩЕНИЙ ---
@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    print(f"[БОТ] Обнаружено удаленное сообщение от {message.author.name}")

    channel = await get_log_channel(message.guild)
    if not channel: return

    embed = discord.Embed(title="🗑️ Сообщение удалено", color=discord.Color.red())
    embed.add_field(name="Автор", value=message.author.mention, inline=True)
    embed.add_field(name="Канал", value=message.channel.mention, inline=True)
    embed.add_field(name="Текст", value=message.content[:1024] or "*Пусто*", inline=False)
    await channel.send(embed=embed)

# --- ВЕБ-ПАНЕЛЬ ---
app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "visual"))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    config = load_config()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"channel_id": config.get("log_channel_id", "")}
    )

@app.post("/update")
async def update_config(channel_id: str = Form(...)):
    config = load_config()
    clean_id = channel_id.replace("<#", "").replace(">", "").strip()
    config["log_channel_id"] = clean_id
    save_config(config)
    return RedirectResponse(url="/", status_code=303)

def run_web():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

if __name__ == "__main__":
    print("Запуск веб-панели на http://127.0.0.1:8000 ...")
    threading.Thread(target=run_web, daemon=True).start()
    print("Запуск Discord бота...")
    bot.run(TOKEN)