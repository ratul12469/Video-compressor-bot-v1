"""
Advanced Video Compressor Bot
Optimized for Termux Deployment
"""
import os
import time
import asyncio
import math
import shutil
from datetime import datetime, timedelta
from aiohttp import web
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait
from dotenv import load_dotenv

# .env ফাইল থেকে কনফিগারেশন লোড করা
load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = [6992010963]  # আপনার অ্যাডমিন আইডি [cite: 2]

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ডিরেক্টরি বা ফোল্ডার তৈরি
DOWNLOAD_DIR = "./downloads/"
TEMP_DIR = "./temp/"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

user_data = {}
admin_states = {}

# --- হেল্পার ফাংশনসমূহ ---
def save_user_data(user_id, username, first_name, last_name):
    username = str(username) if username else "No_Username"
    first_name = str(first_name).replace(",", "")
    last_name = (str(last_name) if last_name else "").replace(",", "")
    exists = False
    try:
        with open("users.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{user_id},"):
                    exists = True
                    break
    except FileNotFoundError:
        pass
    if not exists:
        with open("users.txt", "a", encoding="utf-8") as f:
            f.write(f"{user_id}, {username}, {first_name} {last_name}\n")

def count_users():
    with open("users.txt", "r") as f:
        return len(f.readlines())

def get_all_ids():
    ids = []
    try:
        with open("users.txt", "r", encoding="utf-8") as f:
            for line in f:
                user_id = line.strip().split(",")[0]
                if user_id:
                    ids.append(int(user_id))
    except FileNotFoundError:
        print("No users found yet.")
    return ids

def to_small_caps(text):
    chars = "abcdefghijklmnopqrstuvwxyz"
    small_caps = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    table = str.maketrans(chars, small_caps)
    return text.translate(table)

def humanbytes(size):
    if not size: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0: return f"{size:.2f} {unit}"
        size /= 1024.0

async def progress_bar(current, total, text, message, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        time_to_completion = round((total - current) / speed) if speed > 0 else 0
        progress = "[{0}{1}]".format(
            ''.join(["■" for i in range(math.floor(percentage / 10))]),
            ''.join(["□" for i in range(10 - math.floor(percentage / 10))])
        )
        tmp = f"{text}\n<code>{progress}</code> <b>{round(percentage, 2)}%</b>\n" \
              f"<b>Size:</b> {humanbytes(current)} / {humanbytes(total)}\n" \
              f"<b>Speed:</b> {humanbytes(speed)}/s\n" \
              f"<b>ETA:</b> {str(timedelta(seconds=time_to_completion))}"
        try:
            await message.edit_text(tmp)
        except:
            pass

async def run_ffmpeg(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout, stderr

async def clean_old_files():
    while True:
        now = time.time()
        for root, dirs, files in os.walk(DOWNLOAD_DIR):
            for f in files:
                path = os.path.join(root, f)
                if os.stat(path).st_mtime < now - 1800:
                    try: os.remove(path)
                    except: pass
        await asyncio.sleep(600)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast")],
        [InlineKeyboardButton("🆔 Get All IDs", callback_data="get_ids")],
        [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh")]
    ])

# ক্লায়েন্ট ইনিশিয়ালাইজেশন
app = Client("VideoCompressorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML)

# --- কমান্ড হ্যান্ডলারস ---
@app.on_message(filters.command("admin") & filters.user(ADMIN_IDS))
async def admin(client, message):
    try:
        bot_status_txt = (f"📊 Total Active Users: {count_users()}")
    except:
        bot_status_txt = "No User ID saved in the server yet."
    await message.reply_text(bot_status_txt, reply_markup=get_admin_keyboard())

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user = message.from_user
    save_user_data(user.id, user.username, user.first_name, user.last_name)
    header = to_small_caps("👋 Welcome to Video Compressor Bot!")
    await message.reply_text(
        f"<b>{header}</b>\n\n"
        "🎬 <b>যেকোনো ভিডিও পাঠান</b>, আমি সেটির কোয়ালিটি ঠিক রেখে সাইজ কমিয়ে (Compress) দেব।\n\n"
        "✨ <b>ফিচারসমূহ:</b>\n"
        "📦 ২ জিবি (2GB) পর্যন্ত ভিডিও সাপোর্ট\n"
        "🖼️ কাস্টম থাম্বনেইল সেট করার সুবিধা\n"
        "⚡ সুপার ফাস্ট অটোমেটিক কম্প্রেশন\n\n"
        "📤 <b>শুরু করতে এখনই একটি ভিডিও বা ফাইল পাঠান!</b>\n\n"
        "<i>নোট: কাস্টম থাম্বনেইল ব্যবহার করতে চাইলে ভিডিও পাঠানোর আগে ইমেজটি সেন্ড করুন।</i>"
    )

@app.on_message(filters.video | filters.document)
async def handle_video(client, message: Message):
    user_id = message.from_user.id
    file = message.video or message.document
    if message.document and not file.mime_type.startswith("video/"):
        return
    if user_id in user_data and user_data[user_id].get("task"):
        return await message.reply_text("⚠️ <b>আপনার একটি টাস্ক অলরেডি রানিং আছে। দয়া করে অপেক্ষা করুন!</b>")
    
    user_data[user_id] = {
        "video_msg": message,
        "thumb": user_data.get(user_id, {}).get("thumb"),
        "task": False
    }
    
    buttons = [
        [InlineKeyboardButton("📉 Low (Fastest)", callback_data="comp_low"),
         InlineKeyboardButton("📊 Medium (Balanced)", callback_data="comp_med")],
        [InlineKeyboardButton("🎬 High (Best Quality)", callback_data="comp_high")],
        [InlineKeyboardButton("❌ Cancel Task", callback_data="cancel_task")]
    ]
    
    label_file = to_small_caps("File Received")
    label_size = to_small_caps("Size")
    await message.reply_text(
        f"<b>{label_file}:</b> <code>{file.file_name or 'video.mp4'}</code>\n"
        f"<b>{label_size}:</b> {humanbytes(file.file_size)}\n\n"
        "নিচের যেকোনো একটি কম্প্রেশন অপশন সিলেক্ট করুন:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.private)
async def private_messages_handler(client, message: Message):
    user_id = message.from_user.id
    
    if admin_states.get(user_id) == "waiting_for_msg":
        admin_states[user_id] = None
        if not os.path.exists("users.txt"):
            await message.reply_text("No users to broadcast to.")
            return
        
        users = get_all_ids()
        status = await message.reply_text(f"🚀 Sending to {len(users)} users...")
        success, failed = 0, 0
        
        for uid in users:
            try:
                await message.copy(chat_id=int(uid))
                success += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
                
        await status.edit_text(f"✅ <b>Broadcast Done</b>\nSent: {success} | Failed: {failed}")
        return
        
    if message.photo:
        if user_id not in user_data:
            user_data[user_id] = {}
        path = os.path.join(DOWNLOAD_DIR, f"thumb_{user_id}.jpg")
        await message.download(file_name=path)
        user_data[user_id]["thumb"] = path
        await message.reply_text("✅ <b>Thumbnail saved!</b> এটি আপনার পরবর্তী ভিডিওতে যুক্ত হবে।")

# --- কম্প্রেশন লজিক ---
@app.on_callback_query(filters.regex("^comp_"))
async def compression_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_data or not user_data[user_id].get("video_msg"):
        return await callback.answer("কোথাও ভুল হয়েছে। ভিডিওটি আবার পাঠান।", show_alert=True)
    
    quality = callback.data.split("_")[1]
    user_data[user_id]["task"] = True
    video_msg = user_data[user_id]["video_msg"]
    
    # টার্মাক্স (মোবাইল প্রসেসর) এর জন্য অপ্টিমাইজড FFmpeg কনফিগ
    configs = {
        "low": {"crf": "32", "preset": "ultrafast", "b_v": "600k"},
        "med": {"crf": "26", "preset": "superfast", "b_v": "1200k"},
        "high": {"crf": "22", "preset": "veryfast", "b_v": "2200k"}
    }
    cfg = configs[quality]
    status_msg = await callback.message.edit_text("⏳ <b>ইনিশিয়ালাইজ হচ্ছে...</b>")
    
    try:
        start_time = time.time()
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_input.mp4")
        await status_msg.edit_text("📥 <b>টেলিগ্রাম থেকে ভিডিও ডাউনলোড হচ্ছে...</b>")
        
        await video_msg.download(
            file_name=file_path,
            progress=progress_bar,
            progress_args=("📥 <b>Downloading:</b>", status_msg, start_time)
        )
        
        output_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_compressed.mp4")
        await status_msg.edit_text(f"⚙️ <b>ভিডিও কম্প্রেস হচ্ছে ({quality})... এতে কিছুটা সময় লাগতে পারে।</b>")
        
        # FFmpeg কমান্ড এক্সিকিউশন
        ffmpeg_cmd = (
            f'ffmpeg -i "{file_path}" -c:v libx264 -crf {cfg["crf"]} -preset {cfg["preset"]} '
            f'-b:v {cfg["b_v"]} -maxrate {cfg["b_v"]} -bufsize 1.5M -c:a aac -b:a 96k '
            f'-pix_fmt yuv420p -y "{output_path}"'
        )
        rc, _, err = await run_ffmpeg(ffmpeg_cmd)
        if rc != 0:
            raise Exception(f"FFmpeg error: {err.decode()[-200:]}")
            
        await status_msg.edit_text("📤 <b>কম্প্রেসড ফাইল আপলোড হচ্ছে...</b>")
        start_time = time.time()
        orig_size = os.path.getsize(file_path)
        new_size = os.path.getsize(output_path)
        saving = ((orig_size - new_size) / orig_size) * 100
        thumb = user_data[user_id].get("thumb")
        
        await client.send_video(
            chat_id=callback.message.chat.id,
            video=output_path,
            caption=(
                f"✅ <b>Compression Complete!</b>\n\n"
                f"📁 <b>Original Size:</b> {humanbytes(orig_size)}\n"
                f"📉 <b>Compressed Size:</b> {humanbytes(new_size)}\n"
                f"✨ <b>Space Saved:</b> {saving:.1f}%"
            ),
            thumb=thumb,
            progress=progress_bar,
            progress_args=("📤 <b>Uploading:</b>", status_msg, start_time)
        )
        await status_msg.delete()
        
    except Exception as e:
        await callback.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>")
    finally:
        user_data[user_id]["task"] = False
        if os.path.exists(file_path): os.remove(file_path)
        if os.path.exists(output_path): os.remove(output_path)

# --- অন্যান্য কলব্যাক হ্যান্ডলারস ---
@app.on_callback_query(filters.regex("cancel_task"))
async def cancel_callback(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data.pop(user_id, None)
    await callback.message.edit_text("❌ <b>টাস্ক বাতিল করা হয়েছে এবং ক্যাশ ক্লিয়ার করা হয়েছে।</b>")

@app.on_callback_query(filters.regex("broadcast"))
async def broadcast(client, callback: CallbackQuery):
    admin_states[callback.from_user.id] = "waiting_for_msg"
    await callback.message.edit_text("📝 সব ইউজারদের পাঠানোর জন্য মেসেজটি এখন টাইপ করে পাঠান।")

@app.on_callback_query(filters.regex("get_ids"))
async def get_ids(client, callback: CallbackQuery):
    await callback.answer()
    if os.path.exists("users.txt"):
        await callback.message.reply_document("users.txt", caption="ইউজার লিস্ট ফাইল।")
    else:
        await callback.answer("কোনো ইউজার ডাটা পাওয়া যায়নি!", show_alert=True)

@app.on_callback_query(filters.regex("refresh"))
async def refresh(client, callback: CallbackQuery):
    await callback.answer()
    try: bot_status_txt = (f"📊 Total Active Users: {count_users()}")
    except: bot_status_txt = "No User ID saved yet."
    try: await callback.message.edit_text(bot_status_txt, reply_markup=get_admin_keyboard())
    except: pass

# --- লোকাল ওয়েব সার্ভার এবং স্টার্টআপ ---
async def handle(request):
    return web.Response(text="Termux Bot is perfectly running!")
    
async def main():
    print("--- VideoCompressor Bot Starting ---")
    asyncio.create_task(clean_old_files())
    
    server = web.Application()
    server.router.add_get("/", handle)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    
    await app.start()
    print("--- Bot is Online in Termux ---")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
