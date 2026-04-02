# ✨ Crisper: Universal Video Upscaler

A Modular CLI that offers AI & Math based Video Upscaling.

⚠️ This tool was tested on **Apple's M5 Pro Silicon**. Behaviour may differ on other architectures.

# Features

- Custom PyTorch + MPS Engine: A highly optimized "Zero-PNG" RAM-piping architecture built specifically to exploit Apple Silicon (Metal Performance Shaders) without SSD I/O bottlenecks.
- Dynamic AI Model Support: Seamlessly ingest and use any open-source .pth or .safetensors upscaling models (e.g., RealESRGAN, Nomos, OmniSR, RealCUGAN) with auto-scaling detection.
- Swarm Deployment Protocol: Drastically slash compute times by splitting video files and processing them concurrently across 2, 4, or 6 background terminal nodes.
- Smart Resolution Targeting: Auto-detects input dimensions and intelligently bumps to the next standard broadcast resolution (480p > 720p > 1080p, up to 4K), alongside uncapped strict multipliers (2x, 3x, 4x).
- Hardware-Accelerated Math Scaling: Fast, non-AI mathematical scaling (Lanczos) via FFmpeg, plus a dedicated 16:9 Letterbox tool to enforce standard aspect ratios with black padding.
- Concurrent Execution: Fully isolated workspaces allow you to run multiple instances of Crisper (or deploy multiple Swarms) on different files simultaneously without collision.
- Universal Format Support: Ingests any video format supported by FFmpeg and standardizes the upscaled output to .mp4.

#### Planned Optimizations:

- Dynamic Tensor Caching: Pre-allocating memory buffers in the tile-processing loop to prevent OS garbage collection and speed up Apple Silicon execution.
- Smart Frame Interpolation: Halving upscaler workloads by processing at 30fps and using AI motion-interpolation to smoothly hallucinate back to 60fps upon compilation.

#### Future Ideas:

- Native GUI Application
- Frame Interpolation Plugin (RIFE / 60fps conversion)
- Face Detail Restoration (CodeFormer / GFPGAN integration)
- Audio Enhancements (Noise reduction & voice isolation)
- Image Upscaling Mode (Optimized pipeline for massive static canvases and manga)

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

#### Recommended models:

_(tested on real video, not anime)_

- [realesr-animevideov3.pth](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) **(Balanced & Smoother)** 3.34s / 1m 5.85s `[benchmark]`
- [realesr-general-wdn-x4v3.pth](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) **(More detailed, Less smooth)** 4.97s / 1m 41.73s `[1.5x slower, tiny optimized model]`
- [NCNN_Anime](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) **(Balanced)** 6.28s / 1m 48.37s `[1.7x slower, may vary based on your hardware I/O speeds]`
- [Real_CUGAN_4x.pth](https://huggingface.co/smnorini/Real_CUGAN_4x/tree/main) **(Balanced & Detailed)** 8.23s / 2m 52.99s `[2.6x slower, heavier model]`

# License

MIT License. [(view)](/LICENSE)

# Contributing

Code. Format (Black). Pull Request. 😄

`"--line-length", "88"`
