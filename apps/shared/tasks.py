import subprocess
import os

from pathlib import Path
from django.conf import settings
from datetime import datetime

from apps.shared.utils.logging import logger
from core.celery import app


@app.task
def compress_video_async(video_path: str, media_id: str) -> None:
    """
    Asynchronous task to compress a video file using ffmpeg.
    """
    start = datetime.now()
    logger.info(f"Starting compression for video: {video_path}")

    # Fix: Use container-aware path resolution
    if video_path.startswith('media/'):
        filename = video_path[6:]
        logger.info(f"Here 1")
    else:
        filename = video_path
        logger.info(f"Here 2")

    # Determine the correct input path based on current container
    if os.path.exists('/app/media'):
        input_path = Path('/app/media') / filename
    else:
        # Fallback to MEDIA_ROOT (local development)
        input_path = Path(settings.MEDIA_ROOT) / filename
    logger.info(f"Input path: {input_path}")

    output_path = input_path.with_name(f"compressed_{input_path.name}")
    logger.info(f"Output path: {output_path}")

    command = [
        'ffmpeg',
        "-i", str(input_path),
        "-vcodec", "libx264",
        "-crf", "28",          # 23 = high quality, 28 = smaller file
        "-preset", "veryfast", # tradeoff: slower = smaller
        "-acodec", "aac",
        "-b:a", "128k",
        str(output_path)
    ]

    try:
        # Check if input file exists
        if not input_path.exists():
            logger.error(f"Media: {media_id} | Input file not found: {input_path}")
            return

        logger.info(f"Starting compression...")
        before = input_path.stat().st_size
        subprocess.run(command, check=True)
        after = output_path.stat().st_size
        reduction = 100 * (before - after) / before if before > 0 else 0

        end = datetime.now()
        duration = (end - start).total_seconds()
        logger.info(f"Media: {media_id} | {duration:.2f} seconds | Compressed from {before/1e6:.2f}MB to {after/1e6:.2f}MB ({reduction:.1f}% smaller)")
        # Optionally, replace the original file with the compressed one
        input_path.unlink()  # Remove original file
        output_path.rename(input_path)  # Rename compressed file to original name
    except subprocess.CalledProcessError as e:
        # Handle errors in compression
        logger.error(f"Media: {media_id} | Error compressing video: {e}")
    except FileNotFoundError as e:
        logger.error(f"Media: {media_id} | File not found: {e}")
    except Exception as e:
        logger.error(f"Media: {media_id} | Unexpected error: {e}")
