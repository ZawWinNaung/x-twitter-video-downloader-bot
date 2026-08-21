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

TWITTER_REGEX = r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/([0-9]+)'
MAX_TELEGRAM_SIZE = 50 * 1024 * 1024  # 50 MB


async def get_twitter_media(status_id: str):
    """Extracts a video stream from X/Twitter via vxtwitter API, falling back to lower resolution if > 50MB."""
    api_url = f"https://api.vxtwitter.com/Twitter/status/{status_id}"
    headers = {"User-Agent": "TelegramBot/1.0"}
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(api_url, headers=headers)
        if res.status_code != 200:
            return None, None, None, None
            
        data = res.json()
        media_list = data.get("media_extended", [])
        
        target_media = None
        for media in media_list:
            if media.get("type") in ["video", "gif"]:
                target_media = media
                break
                
        if not target_media:
            return None, None, None, None

        thumb_url = target_media.get("thumbnail_url")
        variants = target_media.get("variants", [])

        # Collect candidate URLs sorted from highest to lowest quality
        video_urls = []
        if variants:
            # Sort variants by bitrate if available (highest bitrate first)
            sorted_variants = sorted(
                [v for v in variants if v.get("content_type") == "video/mp4"],
                key=lambda x: x.get("bitrate", 0),
                reverse=True
            )
            video_urls = [v.get("url") for v in sorted_variants if v.get("url")]

        # Fallback if variants list is empty
        if not video_urls and target_media.get("url"):
            video_urls = [target_media.get("url")]

        video_bytes = None
        
        # Try downloading each resolution candidate until one fits under 50 MB
        for url in video_urls:
            # Send a HEAD request first to check size without downloading full body
            head_resp = await client.head(url)
            content_length = head_resp.headers.get("Content-Length")

            if content_length and int(content_length) > MAX_TELEGRAM_SIZE:
                continue  # Skip this resolution if we know it's over 50MB

            # Download actual video bytes
            v_resp = await client.get(url)
            if v_resp.status_code == 200:
                if len(v_resp.content) <= MAX_TELEGRAM_SIZE:
                    video_bytes = v_resp.content
                    break  # Found an acceptable resolution

        # If all candidates exceeded 50MB during HEAD check, grab smallest candidate as last effort
        if not video_bytes and video_urls:
            smallest_url = video_urls[-1]
            v_resp = await client.get(smallest_url)
            if v_resp.status_code == 200 and len(v_resp.content) <= MAX_TELEGRAM_SIZE:
                video_bytes = v_resp.content

        # Download thumbnail
        thumb_bytes = None
        if thumb_url:
            t_resp = await client.get(thumb_url)
            if t_resp.status_code == 200:
                thumb_bytes = t_resp.content

    return video_bytes, thumb_bytes, None, None


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

    if text.startswith('/start'):
        await bot.send_message(
            chat_id=chat_id,
            text="👋 Send me a video link from **X (Twitter)**!",
            parse_mode="Markdown",
            reply_to_message_id=message_id
        )
        return

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
                text="❌ Video is too large (over 50 MB even at lower resolutions) or couldn't be extracted."
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