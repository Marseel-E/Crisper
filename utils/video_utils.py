__all__ = ["get_video_info", "extract_audio"]

import subprocess
import json


def get_video_info(video_path: str) -> tuple[int, int, float, float]:
    """
    Uses ffprobe to auto-detect size, framerate, and exact duration.

    Parameters:
        video_path: str - The path to the video to probe.

    Returns:
        tuple[int, int, float, float] - width, height, framerate, duration.
    """

    cmd: list[str] = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration",
        "-of",
        "json",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)["streams"][0]

    width: int = int(info["width"])
    height: int = int(info["height"])

    num, den = map(int, info["r_frame_rate"].split("/"))
    fps: float = num / den if den != 0 else 30

    duration: float = float(info.get("duration", 0))

    if duration == 0:
        cmd_fmt: list[str] = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ]
        res_fmt = subprocess.run(cmd_fmt, capture_output=True, text=True)

        duration = float(
            json.loads(res_fmt.stdout).get("format", {}).get("duration", 0)
        )

    return width, height, fps, duration


def extract_audio(input_vid: str, output_audio: str) -> None:
    """
    Safely rips the master audio track.

    Parameters:
        input_vid: str - The path to the input video.
        output_audio: str - The path to where to store the output audio file.
    """

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_vid,
            "-vn",
            "-c:a",
            "copy",
            output_audio,
            "-y",
        ]
    )
