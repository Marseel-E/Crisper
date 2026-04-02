__all__ = ["PyTorch_MPS_Engine"]

import os
import subprocess
import math

import numpy as np
import torch
from spandrel import ModelLoader
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)

from .base_plugin import BaseUpscaler
from utils.config import sys_config


class PyTorch_MPS_Engine(BaseUpscaler):
    name: str = "AI: PyTorch + MPS (Dynamic Model Selection)"
    description: str = "RAM Piping Engine. Select any .safetensors or .pth model."
    is_ai: bool = True

    model_path: str = ""
    needs_tiling: bool = False

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
        super().__init__(
            input_vid, output_vid, width, height, fps, duration, target_height
        )
        self.model = None
        self.device = None
        self.model_scale: int = 2

    def load_engine(self) -> None:
        with self.console.status(
            f"[bold blue]Loading {os.path.basename(self.model_path)} into MPS...",
            spinner="dots",
        ):
            self.device = torch.device(
                "mps" if torch.backends.mps.is_available() else "cpu"
            )
            if self.device.type == "cpu":
                self.console.print(
                    "[bold yellow]Warning:[/bold yellow] MPS not detected. Falling back to CPU."
                )

            if not os.path.exists(self.model_path):
                self.console.print(
                    f"[bold red]Fatal Error:[/bold red] Weights not found at {self.model_path}"
                )
                raise FileNotFoundError(f"Model {self.model_path} missing.")

            loader = ModelLoader()
            model_descriptor = loader.load_from_file(self.model_path)

            self.model_scale = model_descriptor.scale

            self.model = model_descriptor.model
            self.model.to(self.device).half()
            self.model.eval()

    def process_tile(
        self, img_tensor: torch.Tensor, tile_size: int = 512, padding: int = 32
    ) -> torch.Tensor:
        b, c, h, w = img_tensor.shape
        scale = self.model_scale

        output_h, output_w = h * scale, w * scale
        output_tensor = torch.zeros(
            (b, c, output_h, output_w), device=self.device, dtype=torch.float16
        )

        for y in range(0, h, tile_size):
            for x in range(0, w, tile_size):
                y1 = max(0, y - padding)
                y2 = min(h, y + tile_size + padding)
                x1 = max(0, x - padding)
                x2 = min(w, x + tile_size + padding)

                tile = img_tensor[:, :, y1:y2, x1:x2]

                with torch.no_grad():
                    upscaled_tile = self.model(tile)

                oy1, oy2 = y * scale, min((y + tile_size) * scale, output_h)
                ox1, ox2 = x * scale, min((x + tile_size) * scale, output_w)

                sy1 = (y - y1) * scale
                sy2 = sy1 + (oy2 - oy1)
                sx1 = (x - x1) * scale
                sx2 = sx1 + (ox2 - ox1)

                output_tensor[:, :, oy1:oy2, ox1:ox2] = upscaled_tile[
                    :, :, sy1:sy2, sx1:sx2
                ]

        return output_tensor

    def process_frames(self) -> None:
        pass

    def run(self) -> None:
        self.prepare_workspace()
        self.prepare_video()

        self.load_engine()

        self.console.print(
            f"\n⚙️  [bold cyan]Strategy:[/bold cyan] Native {self.model_scale}x Upscale ➡️  Final {self.target_height}p"
        )

        out_width = self.width * self.model_scale
        out_height = self.height * self.model_scale

        read_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            self.input_vid,
            "-f",
            "image2pipe",
            "-pix_fmt",
            "rgb24",
            "-vcodec",
            "rawvideo",
            "-",
        ]

        temp_video_no_audio = f"{self.workspace}/piped_silent.mp4"
        write_cmd = (
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{out_width}x{out_height}",
                "-r",
                str(self.fps),
                "-i",
                "-",
                "-c:v",
                sys_config.video_codec,
            ]
            + sys_config.hardware_args
            + [
                "-vf",
                f"scale=-2:{self.target_height}:flags=lanczos",
                temp_video_no_audio,
                "-y",
            ]
        )

        estimated_total_frames = math.ceil(self.duration * self.fps)
        frame_bytes_size = self.width * self.height * 3

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
                f"[magenta]Processing with {os.path.basename(self.model_path)}...",
                total=estimated_total_frames,
            )

            decoder = subprocess.Popen(
                read_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            encoder = subprocess.Popen(
                write_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
            )

            frames_done = 0

            with torch.no_grad():
                while True:
                    raw_bytes = decoder.stdout.read(frame_bytes_size)
                    if not raw_bytes or len(raw_bytes) != frame_bytes_size:
                        break

                    img_np = (
                        np.frombuffer(raw_bytes, dtype=np.uint8)
                        .copy()
                        .reshape((self.height, self.width, 3))
                    )

                    input_tensor = (
                        torch.from_numpy(img_np)
                        .permute(2, 0, 1)
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    input_tensor = (input_tensor.float() / 255.0).half()

                    if self.needs_tiling:
                        output_tensor = self.process_tile(input_tensor)
                    else:
                        output_tensor = self.model(input_tensor)

                    output_tensor = output_tensor.squeeze(0).clamp(0, 1) * 255.0
                    out_np = output_tensor.byte().permute(1, 2, 0).cpu().numpy()

                    encoder.stdin.write(out_np.tobytes())

                    frames_done += 1
                    progress.update(task, completed=frames_done)

            decoder.stdout.close()
            encoder.stdin.close()
            decoder.wait()
            encoder.wait()

        with self.console.status(
            "[bold magenta]Muxing master audio...", spinner="dots"
        ):
            if os.path.exists(self.audio_file):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        temp_video_no_audio,
                        "-i",
                        self.audio_file,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0?",
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
                import shutil

                shutil.copy(temp_video_no_audio, self.output_vid)

        import shutil

        shutil.rmtree(self.workspace, ignore_errors=True)
        self.console.print(
            f"\n🎉 [bold green]Success![/bold green] Video saved at: [bold]{self.output_vid}[/bold]"
        )
