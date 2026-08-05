import re
import httpx

async def get_instagram_reel(reel_id: str):
    """Extracts Instagram Reel MP4 stream using metadata parsing."""
    clean_id = reel_id.split('?')[0].strip('/')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        # Try ddinstagram page scrape to find the og:video CDN URL
        for service in ["ddinstagram.com", "vxinstagram.com"]:
            try:
                url = f"https://{service}/reel/{clean_id}"
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    html = resp.text
                    # Extract the og:video content URL
                    match = re.search(r'property="og:video(?::secure_url)?"\s+content="([^"]+)"', html)
                    if not match:
                        match = re.search(r'content="([^"]+)"\s+property="og:video', html)
                        
                    if match:
                        video_url = match.group(1).replace("&amp;", "&")
                        # Download raw MP4 bytes
                        v_resp = await client.get(video_url, headers=headers)
                        if v_resp.status_code == 200:
                            return v_resp.content, None, None, None
            except Exception:
                continue

    return None, None, None, None