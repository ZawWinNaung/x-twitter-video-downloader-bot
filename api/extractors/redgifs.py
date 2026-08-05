import httpx
from io import BytesIO
from redgifs.aio import API as RedGifsAPI
from PIL import Image

async def get_redgifs_media(gif_id: str):
    """Extracts high quality MP4 and JPEG thumbnail for RedGIFs."""
    api = RedGifsAPI()
    try:
        await api.login()
    except Exception:
        pass

    gif_data = await api.get_gif(gif_id)
    video_url, thumb_url = None, None
    width, height = None, None

    if gif_data:
        width = getattr(gif_data, 'width', None)
        height = getattr(gif_data, 'height', None)
        if hasattr(gif_data, 'urls') and gif_data.urls:
            video_url = getattr(gif_data.urls, 'hd', None) or getattr(gif_data.urls, 'sd', None)
            thumb_url = getattr(gif_data.urls, 'thumbnail', None) or getattr(gif_data.urls, 'poster', None)

    await api.close()

    if not video_url:
        return None, None, None, None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.redgifs.com/"
    }

    async with httpx.AsyncClient(timeout=25.0, http2=True) as client:
        v_resp = await client.get(video_url, headers=headers, follow_redirects=True)
        video_bytes = v_resp.content if v_resp.status_code == 200 else None
        
        thumb_bytes_out = None
        if thumb_url:
            t_resp = await client.get(thumb_url, headers=headers, follow_redirects=True)
            if t_resp.status_code == 200:
                try:
                    img = Image.open(BytesIO(t_resp.content))
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        bg = Image.new('RGB', img.size, (0, 0, 0))
                        bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
                        img = bg
                    else:
                        img = img.convert('RGB')
                    img.thumbnail((320, 320))
                    out = BytesIO()
                    img.save(out, format='JPEG', quality=85)
                    thumb_bytes_out = out.getvalue()
                except Exception:
                    pass

    return video_bytes, thumb_bytes_out, width, height