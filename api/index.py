import os
import re
import json
import logging
import asyncio
import traceback
from io import BytesIO
from http.server import BaseHTTPRequestHandler
import httpx
from telegram import Update, Bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Matches x.com and twitter.com status links
TWITTER_REGEX = r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/([0-9]+)'


async def get_twitter_media(status_id: str):
    """Extracts highest quality Twitter/X MP4 video stream using public syndication API."""
    syndication_url = f"https://cdn.syndication.twimg.com/tweet-result?id={status_id}&token=x"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        try:
            res = await client.get(syndication_url, headers=headers)
            if res.status_code != 200:
                return None, None, None

            data = res.json()
            
            # Locate video info inside tweet media
            video_info = None
            if "video" in data:
                video_info = data["video"]
            elif "mediaDetails" in data:
                for media in data["mediaDetails"]:
                    if media.get("type") == "video" or media.get("type") == "animated_gif":
                        video_info = media.get("video_info")
                        break

            if not video_info or "variants" not in video_info:
                return None, None, None

            # Filter for MP4 variants and pick highest bitrate / resolution
            mp4_variants = [
                v for v in video_info["variants"] 
                if v.get("content_type") == "video/mp4" and "url" in v
            ]

            if not mp4_variants:
                return None, None, None

            # Sort variants by bitrate (highest quality first)
            mp4_variants.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
            best_video_url = mp4_variants[0]["url"]

            # Download raw MP4 stream
            v_resp = await client.get(best_video_url, headers=headers)
            if v_resp.status_code == 200:
                aspect_ratio = video_info.get("aspect_ratio", [None, None])
                width = aspect_ratio[0] if len(aspect_ratio) > 0 else None
                height = aspect_ratio[1] if len(aspect_ratio) > 1 else None
                return v_resp.content, width, height

        except Exception as e:
            print(f"Error fetching Twitter media: {e}")

    return None, None, None


async def process_update(update_data):
    if not BOT_TOKEN:
        print("CRITICAL ERROR: BOT_TOKEN environment variable is missing!")
        return

    bot = Bot(token=BOT_TOKEN)
    update = Update.de_json(update_data, bot)
    
    if not update or not update.message or not update.message.text:
        return

    message = update.message
    text = message.text
    chat_id = message.chat_id
    message_id = message.message_id

    # Handle /start command
    if text.startswith('/start'):
        await bot.send_message(
            chat_id=chat_id,
            text="👋 Send me a video link from **X (Twitter)**!",
            parse_mode="Markdown",
            reply_to_message_id=message_id
        )
        return

    # Check for Twitter link match
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
        video_bytes, width, height = await get_twitter_media(status_id)

        if video_bytes:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="📤 Uploading video..."
            )
            
            video_file = BytesIO(video_bytes)
            video_file.name = "twitter_video.mp4"

            send_kwargs = {
                "chat_id": chat_id,
                "video": video_file,
                "reply_to_message_id": message_id,
                "supports_streaming": True
            }

            await bot.send_video(**send_kwargs)
            await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            await bot.edit_message_text(
                chat_id=chat_id, 
                message_id=status_msg.message_id, 
                text="❌ Failed to extract video stream. Make sure the tweet contains a native video."
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
        self.wfile.write(b'Twitter Video Downloader Bot active.')