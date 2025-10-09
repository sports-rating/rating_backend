import subprocess
from pathlib import Path
from django.conf import settings

from apps.shared.utils.logging import logger
from core.celery import app


@app.task
def compress_video_async(video_path: str, media_id: str) -> None:
    """
    Asynchronous task to compress a video file using ffmpeg.
    """

    logger.info(f"Starting compression for video: {video_path}")
    input_path = Path(settings.MEDIA_ROOT) / video_path
    output_path = input_path.with_name(f"compressed_{input_path.name}")

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
        before = input_path.stat().st_size
        subprocess.run(command, check=True)
        after = output_path.stat().st_size
        reduction = 100 * (before - after) / before if before > 0 else 0

        logger.info(f"Media: {media_id} | Compressed from {before/1e6:.2f}MB to {after/1e6:.2f}MB ({reduction:.1f}% smaller)")
        # Optionally, replace the original file with the compressed one
        input_path.unlink()  # Remove original file
        output_path.rename(input_path)  # Rename compressed file to original name
    except subprocess.CalledProcessError as e:
        # Handle errors in compression
        logger.error(f"Media: {media_id} | Error compressing video: {e}")
