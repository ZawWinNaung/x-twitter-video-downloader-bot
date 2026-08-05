import os
import re
import json
import logging
import asyncio
import traceback
from io import BytesIO
from http.server import BaseHTTPRequestHandler
from dotenv import load_dotenv
from telegram import Update, Bot

# Imports from api directory
from api.extractors import get_redgifs_media, get_twitter_media, get_instagram_reel, get_reddit_media

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Flexible Regex Patterns
REDGIFS_REGEX = r'(?:https?://)?(?:www\.)?redgifs\.com/watch/([a-zA-Z0-9]+)'
TWITTER_REGEX = r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/([0-9]+)'
INSTA_REGEX   = r'(?:https?://)?(?:www\.)?instagram\.com/(?:reel|reels|p)/([a-zA-Z0-9_-]+)'
REDDIT_REGEX  = r'(?:https?://)?(?:[a-zA-Z0-9-]+\.)?(?:reddit\.com|redd\.it)/[^\s]+'

async def process_update(update_data):
    if not BOT_TOKEN:
        print("CRITICAL ERROR: BOT_TOKEN is missing!")
        return

    bot = Bot(token=BOT_TOKEN)
    update = Update.de_json(update_data, bot)
    
    if not update or not update.message or not update.message.text:
        return

    message = update.message
    text = message.text
    chat_id = message.chat_id
    message_id = message.message_id

    # Handle /start
    if text.startswith('/start'):
        await bot.send_message(
            chat_id=chat_id,
            text="👋 Send me a video link from **RedGIFs, X (Twitter), Instagram Reels, or Reddit**!",
            parse_mode="Markdown",
            reply_to_message_id=message_id
        )
        return

    # Check for platform link matches
    gif_match = re.search(REDGIFS_REGEX, text)
    tw_match = re.search(TWITTER_REGEX, text)
    ig_match = re.search(INSTA_REGEX, text)
    rd_match = re.search(REDDIT_REGEX, text)

    if not any([gif_match, tw_match, ig_match, rd_match]):
        return

    status_msg = await bot.send_message(
        chat_id=chat_id,
        text="🔎 Processing video link...",
        reply_to_message_id=message_id
    )

    video_bytes, thumb_bytes, width, height = None, None, None, None

    try:
        if gif_match:
            video_bytes, thumb_bytes, width, height = await get_redgifs_media(gif_match.group(1))
        elif tw_match:
            video_bytes, thumb_bytes, width, height = await get_twitter_media(tw_match.group(1))
        elif ig_match:
            video_bytes, thumb_bytes, width, height = await get_instagram_reel(ig_match.group(1))
        elif rd_match:
            # Handles any Reddit link format safely
            video_bytes, thumb_bytes, width, height = await get_reddit_media(raw_text=text)

        if video_bytes:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="📤 Uploading video..."
            )
            
            video_file = BytesIO(video_bytes)
            video_file.name = "media.mp4"

            send_kwargs = {
                "chat_id": chat_id,
                "video": video_file,
                "reply_to_message_id": message_id,
                "supports_streaming": True
            }
            if width: send_kwargs["width"] = width
            if height: send_kwargs["height"] = height
            if thumb_bytes: send_kwargs["thumbnail"] = thumb_bytes

            await bot.send_video(**send_kwargs)
            await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="❌ Failed to extract video stream from this link."
            )

    except Exception as e:
        # Print full stack trace to Vercel Logs
        print(f"Unhandled Exception in process_update: {e}")
        traceback.print_exc()
        await bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_msg.message_id, 
            text="❌ Error processing link. Please check server logs."
        )

# Vercel Handler
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
        self.wfile.write(b'Bot backend operational.')