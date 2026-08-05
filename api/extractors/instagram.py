import httpx

async def get_instagram_reel(reel_id: str):
    """Extracts direct MP4 stream for Instagram Reels via ddinstagram proxy."""
    # Using ddinstagram API parser endpoint for serverless compatibility
    api_url = f"https://api.ddinstagram.com/reel/{reel_id}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            res = await client.get(api_url, headers=headers, follow_redirects=True)
            # If direct download link returned
            if res.status_code == 200 and "video" in res.headers.get("content-type", ""):
                return res.content, None, None, None
        except Exception:
            pass

    return None, None, None, None