# ffmpeg -f gdigrab -offset_x 0 -offset_y 0 -framerate 24 -video_size 1920x1080 -i desktop output.mp4
# ffmpeg -f gdigrab -offset_x 0 -offset_y 0 -framerate 24 -video_size 1920x1080 -i desktop -vframes 240 output.mp4

import subprocess
from uuid import uuid4


def capture():
    file_name = str(uuid4())
    status = subprocess.call(
        [
            "ffmpeg",
            "-f",
            "gdigrab",
            "-offset_x",
            "0",
            "-offset_y",
            "0",
            "-framerate",
            "24",
            "-video_size",
            "1920x1080",
            "-i",
            "desktop",
            "-vframes",
            "240",
            "-loglevel",
            "quiet",
            f"temp/{file_name}.mp4",
        ]
    )
    if status != 0:
        raise ValueError(f"Failed to capture screen. Status code: {status}")
    return file_name
