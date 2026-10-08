import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = "@x_twitter_videos_bot"

TWITTER_REGEX = r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/status/([0-9]+)'
MAX_TELEGRAM_SIZE = 50 * 1024 * 1024  # 50 MB