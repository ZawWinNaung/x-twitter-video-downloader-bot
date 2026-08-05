import httpx

async def get_instagram_reel(reel_id: str):
    """Extracts direct MP4 stream for Instagram Reels."""
    clean_reel_id = reel_id.split('?')[0].strip('/')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        api_urls = [
            f"https://api.ddinstagram.com/reel/{clean_reel_id}",
            f"https://api.ddinstagram.com/p/{clean_reel_id}"
        ]

        for api_url in api_urls:
            try:
                res = await client.get(api_url, headers=headers)
                if res.status_code == 200 and "video" in res.headers.get("content-type", ""):
                    return res.content, None, None, None
            except Exception:
                continue

    return None, None, None, None