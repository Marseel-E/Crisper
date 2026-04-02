# ✨ Crisper: Universal Video Upscaler

A Modular CLI that offers AI & Math based Video Upscaling.

⚠️ This tool was tested on **Apple's M5 Pro Silicon**. Behaviour may differ on other architectures.

# Features

- AI upscalers utilizing `RealESRGAN`.
- Custom Metal PyTorch engine.
- Math upscalers (GPU computed).
  - Aspect Ratio tool, converts all resolutions to 16:9, adding black box padding.
- Smart resolution targeting. (480p to 720p, 720p to 1080p, etc.) [Max 4k]
- Uncapped 2X, 3X, and 4X upscaling.
- Swarm tools. (Ability to split a file down 2, 4, or 6 times and compute them simultaneously. This shortens total compute time but increases compute load substantially.)
- Ability to run multiple instances, of the same or different file, using the same or different upscaler. (Including `Swarm` mode)
- Supports ALL video formats that `ffmpeg` supports. (Always outputs to `.mp4`)
- Multi-platform support. Should work on MacOS, Windows, and Linux. (Only tested on Mac)

- ~~Dynamic Tensor Caching~~ (Optimization)

- ~~Native GUI Application~~ (Soon.)

- ~~Frame Interpolation Plugin~~ (Maybe.)
- ~~Face Detail Restoration~~ (Maybe.)
- ~~Audio Enhancements: Noise Reduction & Voice Isolation~~ (Maybe.)
- ~~Image upscaling~~ (Maybe.)

# How To Use

### Step 1 - Install Dependencies

I recommend opening the `requirements.txt` file first to see what you're installing as some dependencies are **Plugin** specific and you can do without them for the core functionality.

```bash
pip install -r Crisper/requirements.txt
```

### Step 2 - Get FFmpeg

**MAC (homebrew)**

```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu/Fedora/Arch btw)**

- Use your distribution's `Package Manager`.

**Windows (manual)**

1. Go to the [FFmpeg download page](https://ffmpeg.org/download.html).
2. Download the latest version.
3. Extract the `.zip` file.
4. Rename the folder to `ffmpeg` for ease of use.
5. Move to your root drive. (`C:\ffmpeg`)
6. Search for `env` or `environment variables` in the Windows search, and select `Edit the system environment variables`.
7. Click the `Environment Variables` button.
8. Under `System Variables`, select the `Path` variable and click `Edit`.
9. Click `New` and add the path to the `bin` folder. (`C:\ffmpeg\bin`)
10. Save changes and exit.
11. Verify by running:
    - If installed correctly you should see the version you installed.

```bash
ffmpeg --version
```

### Step 3 - Get Real-ESRGAN (Required for most AI Plugins)

1. Download [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) (tested on v0.2.5.0)
   - You need the platform specific `.zip` file. (ex. `realesrgan-ncnn-vulkan-20220423-macos.zip`)
   - **(optional)** you can also get the `.pth` (weight) files to run the different **Plugins**, simply download and place them under a `models/` directory inside `crisper/`. [DO NOT RENAME]
2. Un-zip the file to the `crisper/` directory. (If you have a `realesrgan/` directory now, GREAT SUCCESS!)

### Step 4 - Run

```bash
python3 Crisper {input_file_path} {output_file_path}
```

### (optional) Step 5 - Configure

Run

```bash
python3 Crisper
```

Select option 2 `Settings`, and configure it to your liking.

(You could also go into `Config.py`, and pre-config your platform like the `is_mac` config is made.)

# Plugins

The different upscalers, whether AI or Math all live inside a `plugins/` directory, making them completely independent. Meaning if you wish to improve or create a new upscaler, simply create a Python file inside that directory, inherit the `BaseUpscaler` class, and follow the architecture. (Make sure you import it inside the `__init__.py` file in that directory aswell!)

### List of available Plugins:

- `LanczosUpscaler` (Math)
  - Fast and Accurate but just literally upscales, so stuff get smoother and noise is not removed.
- `NCNN_X4Plus` (AI, RealESRGAN, NCNN)
  - The most accurate model for realism, however it is PAINFULLY slow and requires A LOT of computing.
- `NCNN_Anime` (AI, RealESRGAN, NCNN)
  - A more lightweight model, it was designed for Anime/2D Cartoons, however running it on real video does actually give a nice output, it removes all noise, smoothes textures, and cleans up text quite well. It's not X4Plus, but it also doesn't take a century to compute.
- `PyTorch + MPS Engine` (AI, PyTorch, Metal Shading Language)
  - A custom PyTorch engine that pipes the frame data directly to the GPU, saving a bunch of computing time since the SSD doesn't have to work, meaning no read & write until the very end where the output is saved.
  - Also supports a tiling architecture which helps run RAM hog models such as `4xNomos8kSCHAT-L`.
  - To use this, simply find `.pth` and `.safetensors` models on sites like `HuggingFace` or similar, and place them in a `models/` directory inside `Crisper/`, or your own custom directory, just make sure to configure it in the settings.
  - Shouldn't be too hard to port it to other platforms. Good luck!
- **[Outdated/Broken]** ⛔️ ~~`CoreML_SwinIR` (AI, Apple's CoreML, Apple's Neural Engine)~~
  - **This plugin will not work since the new OOP architecture.**
  - Tried utilizing the ANE, but quickly found out that its primarily used for small files, basically any image computing bigger than 512x512 will get re-routed to the GPU instead.
  - Creating a batching system that feeds it 512x512 pixel chunks of each frame escalates compute time to hours compared to minutes on other models so that was scrapped as well.
  - Basically useless, but still a good learn.

# License

MIT License. [(view)](/LICENSE)

# Contributing

Code. Format (Black). Pull Request. 😄

`"--line-length", "88"`
