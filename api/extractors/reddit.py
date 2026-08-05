import httpx

async def get_reddit_media(post_id: str):
    """Extracts Reddit native video stream using Reddit's public JSON API."""
    url = f"https://www.reddit.com/comments/{post_id}.json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(url, headers=headers)
        if res.status_code != 200:
            return None, None, None, None
            
        try:
            data = res.json()
            post_data = data[0]["data"]["children"][0]["data"]
            
            # Check for native video
            media = post_data.get("secure_media") or post_data.get("media")
            if not media or "reddit_video" not in media:
                return None, None, None, None
                
            video_url = media["reddit_video"].get("fallback_url")
            width = media["reddit_video"].get("width")
            height = media["reddit_video"].get("height")
            
            if not video_url:
                return None, None, None, None

            # Fetch MP4 stream
            v_resp = await client.get(video_url, headers=headers)
            video_bytes = v_resp.content if v_resp.status_code == 200 else None
            
            return video_bytes, None, width, height
        except Exception:
            return None, None, None, None