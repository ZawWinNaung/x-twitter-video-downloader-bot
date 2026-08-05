import re
import httpx

async def get_reddit_media(link_id: str = None, raw_text: str = None):
    """Dynamically resolves any Reddit URL structure (/r/, /u/, /s/, redd.it) to direct MP4 stream."""
    
    # Extract the first full Reddit or redd.it URL from the text
    url_match = re.search(r'https?://[^\s]*(?:reddit\.com|redd\.it)/[^\s]+', raw_text or "")
    if not url_match:
        return None, None, None, None

    raw_url = url_match.group(0)

    # Standard browser-like user agent prevents 403 Forbidden on serverless IPs
    headers = {
        "User-Agent": "android:com.app.downloaderbot:v1.0.0 (by /u/reddit_user_1234)"
    }

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        try:
            # 1. Follow short link / user profile redirects to reach the canonical post URL
            res = await client.get(raw_url, headers=headers)
            if res.status_code != 200:
                return None, None, None, None

            # 2. Strip tracking query params (e.g., ?utm_source=...) and construct JSON endpoint
            final_clean_url = str(res.url).split('?')[0].rstrip('/')
            json_url = f"{final_clean_url}.json"

            # 3. Fetch public JSON data from Reddit
            json_res = await client.get(json_url, headers=headers)
            if json_res.status_code != 200:
                return None, None, None, None

            data = json_res.json()
            post_data = data[0]["data"]["children"][0]["data"]

            # 4. Extract video object (handles primary post & crosspost links)
            media = post_data.get("secure_media") or post_data.get("media")
            
            if not media or "reddit_video" not in media:
                crosspost = post_data.get("crosspost_parent_list", [])
                if crosspost and "reddit_video" in crosspost[0].get("media", {}):
                    media = crosspost[0]["media"]
                else:
                    return None, None, None, None

            video_url = media["reddit_video"].get("fallback_url")
            width = media["reddit_video"].get("width")
            height = media["reddit_video"].get("height")

            if not video_url:
                return None, None, None, None

            # 5. Download the raw video stream
            v_resp = await client.get(video_url, headers=headers)
            if v_resp.status_code == 200:
                return v_resp.content, None, width, height

        except Exception:
            pass

    return None, None, None, None