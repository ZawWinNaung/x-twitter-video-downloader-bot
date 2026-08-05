import httpx

async def get_reddit_media(link_id: str):
    """Extracts Reddit native video stream, resolving share links (/s/...) if necessary."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        target_url = f"https://www.reddit.com/comments/{link_id}.json"
        
        res = await client.get(target_url, headers=headers)
        
        if res.status_code != 200:
            share_url = f"https://www.reddit.com/s/{link_id}"
            resolve_res = await client.get(share_url, headers=headers)
            if resolve_res.status_code == 200:
                final_url = str(resolve_res.url).split('?')[0]
                target_url = f"{final_url}.json"
                res = await client.get(target_url, headers=headers)

        if res.status_code != 200:
            return None, None, None, None
            
        try:
            data = res.json()
            post_data = data[0]["data"]["children"][0]["data"]
          
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

            v_resp = await client.get(video_url, headers=headers)
            video_bytes = v_resp.content if v_resp.status_code == 200 else None
            
            return video_bytes, None, width, height
        except Exception:
            return None, None, None, None