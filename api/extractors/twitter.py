import httpx

async def get_twitter_media(status_id: str):
    """Extracts single video stream from X/Twitter via vxtwitter API."""
    api_url = f"https://api.vxtwitter.com/Twitter/status/{status_id}"
    
    headers = {"User-Agent": "TelegramBot/1.0"}
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.get(api_url, headers=headers)
        if res.status_code != 200:
            return None, None, None, None
            
        data = res.json()
        media_list = data.get("media_extended", [])
        
        video_url = None
        thumb_url = None
        
        # Look for the first video in the status
        for media in media_list:
            if media.get("type") == "video":
                video_url = media.get("url")
                thumb_url = media.get("thumbnail_url")
                break
                
        if not video_url:
            return None, None, None, None
            
        # Download video & thumbnail bytes
        v_resp = await client.get(video_url)
        video_bytes = v_resp.content if v_resp.status_code == 200 else None
        
        thumb_bytes = None
        if thumb_url:
            t_resp = await client.get(thumb_url)
            if t_resp.status_code == 200:
                thumb_bytes = t_resp.content

    return video_bytes, thumb_bytes, None, None