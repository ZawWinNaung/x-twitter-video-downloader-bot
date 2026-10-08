import httpx
from api.config import MAX_TELEGRAM_SIZE

async def get_twitter_media(status_id: str):
    """Extracts a video stream from X/Twitter via vxtwitter API."""
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

        video_urls = []
        if variants:
            sorted_variants = sorted(
                [v for v in variants if v.get("content_type") == "video/mp4"],
                key=lambda x: x.get("bitrate", 0),
                reverse=True
            )
            video_urls = [v.get("url") for v in sorted_variants if v.get("url")]

        if not video_urls and target_media.get("url"):
            video_urls = [target_media.get("url")]

        video_bytes = None
        
        for url in video_urls:
            head_resp = await client.head(url)
            content_length = head_resp.headers.get("Content-Length")

            if content_length and int(content_length) > MAX_TELEGRAM_SIZE:
                continue

            v_resp = await client.get(url)
            if v_resp.status_code == 200:
                if len(v_resp.content) <= MAX_TELEGRAM_SIZE:
                    video_bytes = v_resp.content
                    break

        if not video_bytes and video_urls:
            smallest_url = video_urls[-1]
            v_resp = await client.get(smallest_url)
            if v_resp.status_code == 200 and len(v_resp.content) <= MAX_TELEGRAM_SIZE:
                video_bytes = v_resp.content

        thumb_bytes = None
        if thumb_url:
            t_resp = await client.get(thumb_url)
            if t_resp.status_code == 200:
                thumb_bytes = t_resp.content

    return video_bytes, thumb_bytes, None, None