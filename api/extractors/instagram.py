import re
import httpx

async def get_instagram_reel(reel_id: str):
    """Extracts direct Instagram Reel MP4 using multiple public fallback APIs."""
    clean_id = reel_id.split('?')[0].strip('/')
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        # Method 1: Try public Instagram Embed API
        try:
            embed_url = f"https://www.instagram.com/p/{clean_id}/embed/captioned/"
            resp = await client.get(embed_url, headers=headers)
            if resp.status_code == 200:
                # Find video src in embed payload
                match = re.search(r'class="EmbeddedMediaImage"[^>]*src="([^"]+)"', resp.text)
                video_match = re.search(r'video_url\\":\\"(https:[^\\]+)\\"', resp.text) or re.search(r'<video[^>]+src="([^"]+)"', resp.text)
                
                if video_match:
                    direct_url = video_match.group(1).replace("\\u0026", "&").replace("&amp;", "&")
                    v_resp = await client.get(direct_url, headers=headers)
                    if v_resp.status_code == 200:
                        return v_resp.content, None, None, None
        except Exception:
            pass

        # Method 2: Fallback to Rapid/DD Instagram Proxy JSON API
        try:
            dd_api = f"https://ddinstagram.com/images/share/{clean_id}.mp4"
            v_resp = await client.get(dd_api, headers=headers)
            if v_resp.status_code == 200 and len(v_resp.content) > 10000:
                return v_resp.content, None, None, None
        except Exception:
            pass

    return None, None, None, None