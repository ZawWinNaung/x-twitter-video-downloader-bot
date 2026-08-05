import re
import httpx

async def get_reddit_media(link_id: str = None, raw_text: str = None):
    """Extracts direct Reddit video stream by resolving any share or profile link."""
    url_match = re.search(r'https?://[^\s]*(?:reddit\.com|redd\.it)/[^\s]+', raw_text or "")
    if not url_match:
        return None, None, None, None

    raw_url = url_match.group(0)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        try:
            # 1. Resolve redirect to canonical URL
            res = await client.get(raw_url, headers=headers)
            if res.status_code != 200:
                return None, None, None, None

            # 2. Append .json to canonical post URL
            clean_url = str(res.url).split('?')[0].rstrip('/')
            json_url = f"{clean_url}.json"

            json_res = await client.get(json_url, headers=headers)
            if json_res.status_code != 200:
                return None, None, None, None

            data = json_res.json()
            post_data = data[0]["data"]["children"][0]["data"]

            # Check primary post or crosspost
            media = post_data.get("secure_media") or post_data.get("media")
            if not media or "reddit_video" not in media:
                crosspost = post_data.get("crosspost_parent_list", [])
                if crosspost and "reddit_video" in crosspost[0].get("media", {}):
                    media = crosspost[0]["media"]
                else:
                    return None, None, None, None

            rv = media["reddit_video"]
            video_url = rv.get("fallback_url")
            width = rv.get("width")
            height = rv.get("height")

            if not video_url:
                return None, None, None, None

            # Clean URL parameters
            video_url = video_url.split('?')[0]

            # Download MP4
            v_resp = await client.get(video_url, headers=headers)
            if v_resp.status_code == 200:
                return v_resp.content, None, width, height

        except Exception as e:
            print(f"Reddit extractor error: {e}")

    return None, None, None, None