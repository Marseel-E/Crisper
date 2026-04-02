__all__ = ["BaseUpscaler"]

from abc import ABC, abstractmethod

import os
import glob
import math
import shutil
import subprocess

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from utils import sys_config


class BaseUpscaler(ABC):
    """
    Base class to create plugins.

    --- Methods ---
    process_frames() - The main method to implement. Highly specific to each Plugin.
    prepare_workspace(...) - Prepares the workspace to use, ensuring isolation between Plugins.
    prepare_video() - Prepares the input video, ensuring core compatability of all Plugins.
    save_output() - Saves the final video output, ensuring core compatability of all Plugins.
    run() - Runs the Plugin workflow, ensuring behavioural compatability with the core CLI.

    --- Parameters ---
    name: str - The name of the plugin.
    description: str - A short description of the plugin.
    is_ai: bool - Flags if the plugin utilizes AI.

    input_vid: str - The path to the input video.
    output_vid: str - The path to where to store the output video.
    width: int - The video width.
    height: int - The video height.
    fps: float - The video frame rate.
    duration: float - The video duration.
    target_height: int - The target video height.

    console: rich.Console - The Rich library console to use for the

    workspace: str - The name of the workspace
    frames_dir: str - The path of the temporary frames directory.
    upscaled_dir: str - The path of the temporary upscaled frames directory.
    chunks_dir: str - The path of the temporary upscaled video chunks directory.
    audio_file: str - The path of the master audio file of the video.
    ai_scale: str - The scaling factor to use.

    frames_completed_so_far: int - A basic shared counter.
    master_task: N/A - The main task at hand.
    chunk_task: N/A - The current chunked task.
    """

    name: str = "_"
    description: str = "_"
    is_ai: bool = False

    def __init__(
        self,
        input_vid: str,
        output_vid: str,
        width: int,
        height: int,
        fps: float,
        duration: float,
        target_height: int,
    ) -> None:
        self.input_vid: str = input_vid
        self.output_vid: str = output_vid

        self.width: int = width
        self.height: int = height
        self.fps: float = fps
        self.duration: float = duration

        self.target_height: int = target_height

        self.console: Console | None = None

        self.ai_scale: int = 4 if self.target_height > self.height * 2 else 2

        self.frames_completed_so_far: int = 0
        self.master_task = None
        self.chunk_task = None

    def process_frames(self) -> None:
        """
        The main method to implement. Highly specific to each Plugin.
        """
        pass

    def prepare_workspace(self, workspace_prefix: str = "Crisper") -> None:
        """
        Prepares the workspace to use, ensuring isolation between Plugins.
        """

        safe_name: str = os.path.basename(self.input_vid).replace(".", "_")
        workspace_name: str = (
            f"{workspace_prefix}_{self.__class__.__name__}_{safe_name}"
        )

        setattr(self, "workspace", workspace_name)

        setattr(self, "frames_dir", self.workspace + "/temp_frames")
        setattr(self, "upscaled_dir", self.workspace + "/temp_upscaled")
        setattr(self, "chunks_dir", self.workspace + "/upscaled_chunks")

        os.makedirs(self.chunks_dir, exist_ok=True)

    def prepare_video(self) -> None:
        """
        Prepares the input video, ensuring core compatability of all Plugins.
        """

        setattr(self, "audio_file", self.workspace + "/full_audio.m4a")

        if not os.path.exists(self.audio_file):
            with self.console.status(
                "[bold magenta]Ripping master audio track...", spinner="dots"
            ):
                try:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-i",
                            self.input_vid,
                            "-vn",
                            "-c:a",
                            "copy",
                            self.audio_file,
                            "-y",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    pass  # Swarm mode edge case. Ugly behaviour but works.

    def save_output(self) -> None:
        """
        Saves the final video output, ensuring core compatability of all Plugins.
        """

        with self.console.status(
            "[bold magenta]Welding blocks and reattaching audio...", spinner="dots"
        ):
            concat_file: str = f"{self.workspace}/concat.txt"

            with open(concat_file, "w") as f:
                for chunk_path in sorted(glob.glob(f"{self.chunks_dir}/*.mp4")):
                    f.write(f"file '{os.path.abspath(chunk_path)}'\n")

            temp_video: str = f"{self.workspace}/merged_video.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_file,
                    "-c",
                    "copy",
                    temp_video,
                    "-y",
                ],
                check=True,
            )

            if os.path.exists(self.audio_file):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        temp_video,
                        "-i",
                        self.audio_file,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        self.output_vid,
                        "-y",
                    ],
                    check=True,
                )
            else:
                shutil.copy(temp_video, self.output_vid)

        shutil.rmtree(self.workspace, ignore_errors=True)
        self.console.print(
            f"\n🎉 [bold green]Success![/bold green] Video saved at: [bold]{self.output_vid}[/bold]"
        )

    def run(self) -> None:
        """
        Runs the Plugin workflow, ensuring behavioural compatability with the core CLI.
        """

        self.prepare_workspace()
        self.prepare_video()

        self.console.print(
            f"\n⚙️  [bold cyan]Strategy:[/bold cyan] AI {self.ai_scale}x ➡️  Final {self.target_height}p (Caching & OS-Aware HW Encode Enabled)"
        )

        chunk_duration: int = sys_config.chunk_duration
        total_chunks: int = math.ceil(self.duration / chunk_duration)
        estimated_total_frames: int = math.ceil(self.duration * self.fps)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("• ETA:"),
            TimeRemainingColumn(),
            console=self.console,
        ) as master_progress:
            self.progress = master_progress

            self.master_task = master_progress.add_task(
                "[bold yellow]Total Video Progress", total=estimated_total_frames
            )
            self.chunk_task = master_progress.add_task(
                "[cyan]Initializing Engine...", total=1
            )

            for i in range(total_chunks):
                start_time: int = i * chunk_duration
                upscaled_chunk_path: str = f"{self.chunks_dir}/chunk_{i:04d}.mp4"

                if os.path.exists(upscaled_chunk_path):
                    cached_frames: int = math.ceil(
                        min(chunk_duration, self.duration - start_time) * self.fps
                    )
                    self.frames_completed_so_far += cached_frames

                    master_progress.update(
                        self.master_task, completed=self.frames_completed_so_far
                    )
                    master_progress.print(
                        f"[dim]⏭️  Skipped Block {i+1}/{total_chunks} (Already Cached)[/dim]"
                    )

                    continue

                os.makedirs(self.frames_dir, exist_ok=True)
                os.makedirs(self.upscaled_dir, exist_ok=True)

                master_progress.update(
                    self.chunk_task,
                    description=f"[cyan]Extracting frames for Block {i+1}...",
                    completed=0,
                )

                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-ss",
                        str(start_time),
                        "-i",
                        self.input_vid,
                        "-t",
                        str(chunk_duration),
                        "-r",
                        str(self.fps),
                        f"{self.frames_dir}/frame_%08d.png",
                        "-y",
                    ]
                )

                if len(glob.glob(f"{self.frames_dir}/*.png")) == 0:
                    continue

                self.process_frames()

                master_progress.update(
                    self.chunk_task,
                    description=f"[green]Hardware Encoding Block {i+1}...",
                )

                compile_cmd: list[str] = (
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-framerate",
                        str(self.fps),
                        "-i",
                        f"{self.upscaled_dir}/frame_%08d.png",
                        "-c:v",
                        sys_config.video_codec,
                    ]
                    + sys_config.hardware_args
                    + [
                        "-vf",
                        f"scale=-2:{self.target_height}:flags=lanczos",
                        upscaled_chunk_path,
                        "-y",
                    ]
                )

                subprocess.run(compile_cmd, check=True)

                master_progress.print(
                    f"✅ [bold green]Block {i+1}/{total_chunks} compiled.[/bold green]"
                )

                shutil.rmtree(self.frames_dir, ignore_errors=True)
                shutil.rmtree(self.upscaled_dir, ignore_errors=True)

        self.save_output()
