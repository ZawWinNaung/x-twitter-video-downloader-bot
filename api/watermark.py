import os
import tempfile
import asyncio
import logging
from api.config import BOT_USERNAME

async def add_text_watermark(video_bytes: bytes, watermark_text: str = BOT_USERNAME) -> bytes:
    """Adds a text watermark to video bytes using FFmpeg asynchronously."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_in:
        temp_in.write(video_bytes)
        input_path = temp_in.name

    output_path = input_path.replace(".mp4", "_wm.mp4")

    # Bottom-right corner watermark with semi-transparent background box
    filter_expr = (
        f"drawtext=text='{watermark_text}':"
        f"x=W-tw-20:y=H-th-20:"
        f"fontsize=24:fontcolor=white@0.9:"
        f"box=1:boxcolor=black@0.5:boxborderw=6"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", filter_expr,
        "-c:a", "copy",
        "-preset", "ultrafast",
        output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                processed_bytes = f.read()
            return processed_bytes

        return video_bytes

    except Exception as e:
        logging.warning(f"Watermark processing failed: {e}. Returning original video.")
        return video_bytes

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)