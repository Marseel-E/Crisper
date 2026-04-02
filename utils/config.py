__all__ = ["sys_config"]

import sys
import os
import json

CONFIG_FILE: str = "crisper_config.json"


class HardwareConfig:
    def __init__(self) -> None:
        self.os_name: str = sys.platform

        self.is_mac: bool = self.os_name == "darwin"
        self.is_windows: bool = self.os_name == "win32"
        self.is_linux: bool = self.os_name.startswith("linux")

        # Universal Config
        self.video_codec: str = "libx265"
        self.hardware_args: list[str] = [
            "-crf",
            "17",  # Visually lossless
            "-preset",
            "fast",  # Good balance of speed/compression
            "-pix_fmt",
            "yuv420p",
        ]

        self.chunk_duration: int = 5

        self.ncnn_binary_path: str = "./realesrgan/realesrgan-ncnn-vulkan"
        self.ncnn_models_path: str = "./realesrgan/models"
        self.ncnn_thread_split: str = "4:4:4"

        self.pytorch_models_path: str = "/models"

        # Mac Config
        if self.is_mac:
            self.video_codec = "hevc_videotoolbox"
            self.hardware_args = ["-q:v", "60", "-tag:v", "hvc1", "-pix_fmt", "yuv420p"]

        self.load()

    def load(self) -> None:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    user_data = json.load(f)

                    for key, val in user_data.items():
                        if hasattr(self, key):
                            setattr(self, key, val)
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save(self) -> None:
        data = {
            "video_codec": self.video_codec,
            "hardware_args": self.hardware_args,
            "chunk_duration": self.chunk_duration,
            "ncnn_binary_path": self.ncnn_binary_path,
            "ncnn_models_path": self.ncnn_models_path,
            "ncnn_thread_split": self.ncnn_thread_split,
            "pytorch_models_path": self.pytorch_models_path,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)


sys_config = HardwareConfig()
