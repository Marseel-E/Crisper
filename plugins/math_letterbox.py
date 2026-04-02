__all__ = ["LetterboxPadder"]

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


class LetterboxPadder(BaseUpscaler):
    name: str = "Other: 16:9 Letterbox (Adds Black Padding. NOT AN UPSCALER)"
    description: str = "Forces odd video dimensions into a perfect 16:9 format."

    def run(self) -> None:
        target_width: int = int((self.target_height * 16) / 9)
        self.console.print(
            f"\n⚙️  [bold cyan]Processing Strategy:[/bold cyan] 16:9 Letterbox ➡️  {target_width}x{self.target_height}"
        )

        vf_string: str = (
            f"scale={target_width}:{self.target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2:black"
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
                vf_string,
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
                "[bold magenta]Applying padding and encoding...",
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
            f"\n🎉 [bold green]Success![/bold green] Video letterboxed to [bold]{target_width}x{self.target_height}[/bold]: {self.output_vid}"
        )
