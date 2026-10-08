import re
import json
import asyncio
import traceback
from io import BytesIO
from http.server import BaseHTTPRequestHandler
from telegram import Update, Bot

from api.config import BOT_TOKEN, TWITTER_REGEX
from api.twitter import get_twitter_media
from api.watermark import add_text_watermark


async def process_update(update_data):
    if not BOT_TOKEN:
        print("CRITICAL ERROR: BOT_TOKEN is missing!")
        return

    bot = Bot(token=BOT_TOKEN)
    update = Update.de_json(update_data, bot)
    
    # 1. Guard check for update and message
    if not update or not update.message:
        return

    message = update.message
    raw_text = message.text

    # 2. Guard check: Ensure text exists and is strictly a string (Fixes Pylance None Type Error)
    if not raw_text or not isinstance(raw_text, str):
        return

    text: str = raw_text
    chat_id = message.chat_id
    message_id = message.message_id

    # 3. Safe startswith check
    if text.startswith('/start'):
        await bot.send_message(
            chat_id=chat_id,
            text="👋 Send me a video link from **X (Twitter)**!",
            parse_mode="Markdown",
            reply_to_message_id=message_id
        )
        return

    # 4. Safe regex search with string guaranteed
    tw_match = re.search(TWITTER_REGEX, text)
    if not tw_match:
        return

    status_msg = await bot.send_message(
        chat_id=chat_id,
        text="🔎 Processing Twitter video link...",
        reply_to_message_id=message_id
    )

    try:
        status_id = tw_match.group(1)
        video_bytes, thumb_bytes, width, height = await get_twitter_media(status_id)

        if video_bytes:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="🎨 Applying watermark..."
            )
            
            # Apply FFmpeg watermark (@x_twitter_videos_bot)
            watermarked_bytes = await add_text_watermark(video_bytes)

            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="📤 Uploading video..."
            )
            
            video_file = BytesIO(watermarked_bytes)
            video_file.name = "twitter_video.mp4"

            send_kwargs = {
                "chat_id": chat_id,
                "video": video_file,
                "reply_to_message_id": message_id,
                "supports_streaming": True
            }

            if thumb_bytes:
                thumb_file = BytesIO(thumb_bytes)
                thumb_file.name = "thumb.jpg"
                send_kwargs["thumbnail"] = thumb_file

            await bot.send_video(**send_kwargs)
            await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="❌ Video is too large (over 50 MB) or couldn't be extracted."
            )

    except Exception as e:
        print(f"Unhandled Exception: {e}")
        traceback.print_exc()
        await bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_msg.message_id, 
            text="❌ Error processing link. Please try again later."
        )


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length).decode('utf-8'))
            asyncio.run(process_update(data))
        except Exception as e:
            print(f"Handler POST Error: {e}")
            traceback.print_exc()
            
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Twitter Downloader Bot operational.')