__all__ = ["NCNN_X4Plus", "NCNN_Anime"]

import subprocess
import glob
import time

from .base_plugin import BaseUpscaler

from utils import sys_config


class BaseNCNNUpscaler(BaseUpscaler):
    is_ai: bool = True

    model_name: str = "_"

    def process_frames(self) -> None:
        chunk_frames: int = len(glob.glob(f"{self.frames_dir}/*.png"))

        if chunk_frames == 0:
            return

        ncnn_cmd: list[str] = [
            sys_config.ncnn_binary_path,
            "-i",
            self.frames_dir,
            "-o",
            self.upscaled_dir,
            "-s",
            str(self.ai_scale),
            "-n",
            self.model_name,
            "-m",
            sys_config.ncnn_models_path,
            "-j",
            sys_config.ncnn_thread_split,
        ]

        if hasattr(self, "progress"):
            self.progress.update(
                self.chunk_task,
                description=f"[magenta]AI Upscaling Block...",
                total=chunk_frames,
                completed=0,
            )

        process = subprocess.Popen(
            ncnn_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        while process.poll() is None:
            count = len(glob.glob(f"{self.upscaled_dir}/*.png"))

            if hasattr(self, "progress"):
                self.progress.update(self.chunk_task, completed=count)
                self.progress.update(
                    self.master_task, completed=self.frames_completed_so_far + count
                )

            time.sleep(0.5)

        count = len(glob.glob(f"{self.upscaled_dir}/*.png"))

        if hasattr(self, "progress"):
            self.progress.update(self.chunk_task, completed=count)
            self.progress.update(
                self.master_task, completed=self.frames_completed_so_far + count
            )

        self.frames_completed_so_far += chunk_frames


class NCNN_X4Plus(BaseNCNNUpscaler):
    name: str = "AI: realesrgan-x4plus"
    description: str = "Photorealistic, Detailed output, Very slow"

    model_name: str = "realesrgan-x4plus"

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

        # This model ONLY supports 4x scaling
        self.ai_scale = 4


class NCNN_Anime(BaseNCNNUpscaler):
    name: str = "AI: realesr-animevideov3"
    description: str = "Anime/Cartoon, Smoothed output, Fast."

    model_name: str = "realesr-animevideov3"

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

        if self.target_height > self.height * 3:
            self.ai_scale = 4
        elif self.target_height > self.height * 2:
            self.ai_scale = 3
        else:
            self.ai_scale = 2
