__all__ = ["LanczosUpscaler"]

import subprocess
import math

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .base_plugin import BaseUpscaler

from utils import sys_config


class LanczosUpscaler(BaseUpscaler):
    name: str = "Math: Lanczos"
    description: str = "The absolute best efficiency to quality ratio."

    def run(self) -> None:
        self.console.print(
            f"\n⚙️  [bold cyan]Processing Strategy:[/bold cyan] Direct FFmpeg Lanczos ➡️  {self.target_height}p"
        )

        ffmpeg_math: list[str] = (
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-progress",
                "pipe:1",
                "-nostats",
                "-i",
                self.input_vid,
                "-vf",
                f"scale=-2:{self.target_height}:flags=lanczos",
                "-c:v",
                sys_config.video_codec,
            ]
            + sys_config.hardware_args
            + ["-c:a", "copy", self.output_vid, "-y"]
        )

        estimated_total_frames: int = math.ceil(self.duration * self.fps)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("• ETA:"),
            TimeRemainingColumn(),
            console=self.console,
        ) as progress:

            task = progress.add_task(
                "[bold magenta]Applying mathematical scaling...",
                total=estimated_total_frames,
            )

            process = subprocess.Popen(
                ffmpeg_math, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                if "frame=" in line:
                    try:
                        frame_str = line.split("=")[1].strip()
                        if frame_str.isdigit():
                            progress.update(task, completed=int(frame_str))
                    except ValueError:
                        pass
            process.wait()

        self.console.print(
            f"\n🎉 [bold green]Success![/bold green] Video mathematically scaled: [bold]{self.output_vid}[/bold]"
        )
