__all__ = [
    # "CoreML_SwinIR"
]  # BROKEN & OUTDATED

import subprocess
import os
import shutil
import glob
import math
from PIL import Image
import numpy as np
import coremltools as cmt
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .base_plugin import BaseUpscaler


class CoreML_SwinIR(BaseUpscaler):
    name: str = (
        "[Broken] AI: CoreML Engine (MACos-ARM REQUIRED) [Python=<3.11 REQUIRED]"
    )
    description: str = (
        "Extremely power-efficient, uses newer Apple Silicon's ANE. (Currently pointless as it off-loads the heavy-lifting to the GPU by Apple's design. As the ANE cannot process big files.)"
    )
    is_ai: bool = True

    model_path: str = "models/realesr-general-x4v3.mlpackage"

    def run(
        self,
        input_vid: str,
        output_vid: str,
        width: int,
        height: int,
        fps: float,
        duration: float,
        target_height: int,
        console,
    ) -> None:
        console.print(
            f"\n⚙️  [bold cyan]Strategy:[/bold cyan] Native CoreML ➡️  Final {target_height}p (Neural Engine Active)"
        )

        safe_name: str = os.path.basename(input_vid).replace(".", "_")
        workspace: str = f"workspace_ai_coreml_{safe_name}"

        upscaled_chunks_dir: str = f"{workspace}/upscaled_chunks"
        frames_dir: str = f"{workspace}/temp_frames"
        upscaled_dir: str = f"{workspace}/temp_upscaled"

        os.makedirs(upscaled_chunks_dir, exist_ok=True)
        audio_file: str = f"{workspace}/full_audio.m4a"

        if not os.path.exists(audio_file):
            with console.status(
                "[bold magenta]Ripping master audio track...", spinner="dots"
            ):
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
                        audio_file,
                        "-y",
                    ]
                )

        if not os.path.exists(self.model_path):
            console.print(
                f"\n[bold red]Error:[/bold red] CoreML model not found at {self.model_path}"
            )

            return

        with console.status(
            "[bold blue]Waking up the Apple Neural Engine...", spinner="dots"
        ):
            model = cmt.models.MLModel(
                self.model_path, compute_units=cmt.ComputeUnit.ALL
            )

        chunk_duration: int = 5
        total_chunks: int = math.ceil(duration / chunk_duration)
        estimated_total_frames: int = math.ceil(duration * fps)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("• ETA:"),
            TimeRemainingColumn(),
            console=console,
        ) as master_progress:

            master_task = master_progress.add_task(
                "[bold yellow]Total Video Progress", total=estimated_total_frames
            )
            chunk_task = master_progress.add_task(
                "[cyan]Initializing Engine...", total=1
            )
            frames_completed_so_far: int = 0

            for i in range(total_chunks):
                start_time = i * chunk_duration
                upscaled_chunk_path: str = f"{upscaled_chunks_dir}/chunk_{i:04d}.mp4"

                if os.path.exists(upscaled_chunk_path):
                    cached_frames = math.ceil(
                        min(chunk_duration, duration - start_time) * fps
                    )
                    frames_completed_so_far += cached_frames
                    master_progress.update(
                        master_task, completed=frames_completed_so_far
                    )
                    master_progress.print(
                        f"[dim]⏭️  Skipped Block {i+1}/{total_chunks} (Already Cached)[/dim]"
                    )
                    continue

                os.makedirs(frames_dir, exist_ok=True)
                os.makedirs(upscaled_dir, exist_ok=True)

                master_progress.update(
                    chunk_task,
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
                        input_vid,
                        "-t",
                        str(chunk_duration),
                        "-r",
                        str(fps),
                        f"{frames_dir}/frame_%08d.png",
                        "-y",
                    ]
                )

                frames = sorted(glob.glob(f"{frames_dir}/*.png"))
                if not frames:
                    continue

                master_progress.update(
                    chunk_task,
                    description=f"[magenta]Neural Engine Upscaling Block {i+1}/{total_chunks}...",
                    total=len(frames),
                    completed=0,
                )

                for frame_path in frames:
                    img = Image.open(frame_path).convert("RGB")

                    prediction = model.predict({"image": img})
                    output_key = list(prediction.keys())[0]

                    raw_array = prediction[output_key]
                    img_array = np.squeeze(raw_array)

                    img_array = np.nan_to_num(
                        img_array, nan=0.0, posinf=1.0, neginf=0.0
                    )

                    img_array = np.clip(img_array * 255.0, 0, 255)
                    img_array = img_array.astype(np.uint8)
                    img_array = np.transpose(img_array, (1, 2, 0))

                    high_res_img = Image.fromarray(img_array)

                    out_path = os.path.join(upscaled_dir, os.path.basename(frame_path))
                    high_res_img.save(out_path)

                    frames_completed_so_far += 1
                    master_progress.update(chunk_task, advance=1)
                    master_progress.update(
                        master_task, completed=frames_completed_so_far
                    )

                master_progress.update(
                    chunk_task, description=f"[green]Hardware Encoding Block {i+1}..."
                )

                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-framerate",
                        str(fps),
                        "-i",
                        f"{upscaled_dir}/frame_%08d.png",
                        "-c:v",
                        "hevc_videotoolbox",
                        "-q:v",
                        "60",
                        "-tag:v",
                        "hvc1",
                        "-pix_fmt",
                        "yuv420p",
                        "-vf",
                        f"scale=-2:{target_height}:flags=lanczos",
                        upscaled_chunk_path,
                        "-y",
                    ],
                    check=True,
                )

                shutil.rmtree(frames_dir, ignore_errors=True)
                shutil.rmtree(upscaled_dir, ignore_errors=True)

                master_progress.print(
                    f"✅ [bold green]Block {i+1}/{total_chunks} upscaled via CoreML.[/bold green]"
                )

        with console.status(
            "[bold magenta]Welding precise time-blocks and reattaching audio...",
            spinner="dots",
        ):
            concat_file: str = f"{workspace}/concat.txt"
            with open(concat_file, "w") as f:
                for chunk_path in sorted(glob.glob(f"{upscaled_chunks_dir}/*.mp4")):
                    f.write(f"file '{os.path.abspath(chunk_path)}'\n")

            temp_video_only: str = f"{workspace}/merged_video_no_audio.mp4"
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
                    temp_video_only,
                    "-y",
                ],
                check=True,
            )

            if os.path.exists(audio_file):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        temp_video_only,
                        "-i",
                        audio_file,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        output_vid,
                        "-y",
                    ],
                    check=True,
                )
            else:
                shutil.copy(temp_video_only, output_vid)

        shutil.rmtree(workspace, ignore_errors=True)

        console.print(
            f"\n🎉 [bold green]Success![/bold green] Native Apple Silicon video saved at: [bold]{output_vid}[/bold]"
        )
