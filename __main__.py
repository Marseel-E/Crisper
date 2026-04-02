import sys
import os
import argparse
import inspect
import time

from rich.console import Console
from rich.panel import Panel

import questionary

from utils import get_video_info, run_swarm
from utils.config import sys_config
import plugins
from plugins import BaseUpscaler

console = Console()
STANDARD_RES: list[int] = [144, 240, 360, 480, 720, 1080, 1440, 2160]


def load_plugins() -> dict[str, object]:
    loaded_plugins: dict[str, object] = {}

    for _, obj in inspect.getmembers(plugins):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseUpscaler)
            and obj is not BaseUpscaler
        ):
            loaded_plugins[obj.__name__] = obj

    return loaded_plugins


def format_time(seconds: float) -> str:
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{int(hours)}h {int(mins)}m {secs:.2f}s"


def settings_menu() -> None:
    while True:
        choice = questionary.select(
            "⚙️  Crisper Configuration:",
            choices=[
                f"1. Chunk Duration ({sys_config.chunk_duration}s)",
                f"2. NCNN Threads ({sys_config.ncnn_thread_split})",
                f"3. Video Codec ({sys_config.video_codec})",
                f"4. NCNN Binary Path ({sys_config.ncnn_binary_path})",
                f"5. NCNN Models Path ({sys_config.ncnn_models_path})",
                f"6. PyTorch Models Path ({sys_config.pytorch_models_path})",
                "Back to Main Menu",
            ],
        ).ask()

        if choice == "Back to Main Menu" or not choice:
            break

        if choice.startswith("1"):
            new_val = questionary.text(
                "Enter new chunk duration (seconds):",
                default=str(sys_config.chunk_duration),
            ).ask()
            if new_val and new_val.isdigit():
                sys_config.chunk_duration = int(new_val)
        elif choice.startswith("2"):
            new_val = questionary.text(
                "Enter NCNN thread split (load:decode:encode):",
                default=sys_config.ncnn_thread_split,
            ).ask()
            if new_val:
                sys_config.ncnn_thread_split = new_val
        elif choice.startswith("3"):
            new_val = questionary.text(
                "Enter FFmpeg video codec:", default=sys_config.video_codec
            ).ask()
            if new_val:
                sys_config.video_codec = new_val
        elif choice.startswith("4"):
            new_val = questionary.text(
                "Enter NCNN Binary Path:", default=sys_config.ncnn_binary_path
            ).ask()
            if new_val:
                sys_config.ncnn_binary_path = new_val
        elif choice.startswith("5"):
            new_val = questionary.text(
                "Enter NCNN Models Path:", default=sys_config.ncnn_models_path
            ).ask()
            if new_val:
                sys_config.ncnn_models_path = new_val
        elif choice.startswith("6"):
            new_val = questionary.text(
                "Enter PyTorch Models Path:", default=sys_config.pytorch_models_path
            ).ask()
            if new_val:
                sys_config.pytorch_models_path = new_val

        sys_config.save()
        console.print("[green]Saved![/green]")


def run_upscale_flow(args, available_plugins) -> None:
    if not args.input_vid:
        args.input_vid = questionary.path("Select Input Video:").ask()
        if not args.input_vid:
            return

    if not args.output_vid:
        args.output_vid = questionary.text(
            "Enter Output Path (e.g. output.mp4):", default="output.mp4"
        ).ask()
        if not args.output_vid:
            return

    try:
        width, height, fps, duration = get_video_info(args.input_vid)
    except Exception:
        console.print("[bold red]Error:[/bold red] Could not read video file.")
        return

    console.print(
        f"\n🎬 [bold green]Original Video:[/bold green] {width}x{height} @ {fps:.2f}fps ({duration:.2f} seconds)\n"
    )

    next_tier = height
    for res in STANDARD_RES:
        if res > height:
            next_tier = res
            break

    next_tier_label = (
        f"Smart Tier Up (Target: {next_tier}p)"
        if next_tier > height
        else "Smart Tier Up (Already 4K+)"
    )

    scale_choice = questionary.select(
        "How much larger do you want the video?",
        choices=[
            next_tier_label,
            "Strict 2x Scale",
            "Strict 3x Scale",
            "Strict 4x Scale",
            "Cancel",
        ],
    ).ask()

    if not scale_choice or scale_choice == "Cancel":
        return

    target_height = height * 4
    if scale_choice.startswith("Smart"):
        target_height = next_tier
    elif scale_choice.startswith("Strict 3x"):
        target_height = height * 3
    elif scale_choice.startswith("Strict 2x"):
        target_height = height * 2

    plugin_menu = {
        f"{cls.name} ({cls.description})": k for k, cls in available_plugins.items()
    }
    engine_choice_label = questionary.select(
        "Select the Upscaling Engine:", choices=list(plugin_menu.keys())
    ).ask()

    if not engine_choice_label:
        return

    plugin_class_name = plugin_menu[engine_choice_label]
    plugin_class = available_plugins[plugin_class_name]

    selected_model_path = ""
    needs_tiling = False

    if plugin_class_name == "PyTorch_MPS_Engine":
        base_path = sys_config.pytorch_models_path
        models_dict = {}

        if os.path.exists(base_path):
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith((".pth", ".safetensors")):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, base_path)
                        models_dict[rel_path] = full_path

        if not models_dict:
            console.print(
                f"[bold red]Error:[/bold red] No .pth or .safetensors found in [bold]{base_path}[/bold]"
            )
            return

        model_choice = questionary.select(
            "Select PyTorch Model Weights:", choices=list(models_dict.keys())
        ).ask()

        if not model_choice:
            return
        selected_model_path = models_dict[model_choice]

        needs_tiling = questionary.confirm(
            "Enable VRAM Tiling? (Say 'Yes' for heavy models like Nomos. Say 'No' for lightweight models)",
            default=False,
        ).ask()

    swarm_choice = questionary.select(
        "Deployment Mode:",
        choices=[
            "Standard (Single Instance)",
            "Swarm 2 Nodes",
            "Swarm 4 Nodes",
            "Swarm 6 Nodes",
        ],
    ).ask()

    start_time = time.time()

    if "Swarm" in swarm_choice:
        num_nodes = int(swarm_choice.split()[1])
        run_swarm(
            args.input_vid,
            args.output_vid,
            num_nodes,
            target_height,
            plugin_class_name,
            model_path=selected_model_path,
            needs_tiling=needs_tiling,
        )
    else:
        active_plugin = plugin_class(
            args.input_vid, args.output_vid, width, height, fps, duration, target_height
        )

        if plugin_class_name == "PyTorch_MPS_Engine":
            active_plugin.model_path = selected_model_path
            active_plugin.needs_tiling = needs_tiling

        active_plugin.console = console
        active_plugin.run()

    elapsed_time = time.time() - start_time
    console.print(
        f"\n⏱️  [bold cyan]Total Processing Time:[/bold cyan] {format_time(elapsed_time)}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="✨ Crisper: Universal Video Upscaler")
    parser.add_argument("input_vid", nargs="?", help="Input video file")
    parser.add_argument("output_vid", nargs="?", help="Output video file")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--plugin", type=str)
    parser.add_argument("--height", type=int)

    parser.add_argument("--model_path", type=str, default="")
    parser.add_argument("--tiling", action="store_true")

    args, _ = parser.parse_known_args()
    available_plugins = load_plugins()

    if args.headless:
        if not args.plugin or not args.height:
            return
        try:
            width, height, fps, duration = get_video_info(args.input_vid)
            plugin_class = available_plugins[args.plugin]
            active_plugin = plugin_class(
                args.input_vid,
                args.output_vid,
                width,
                height,
                fps,
                duration,
                args.height,
            )

            if args.model_path:
                active_plugin.model_path = args.model_path
            if args.tiling:
                active_plugin.needs_tiling = True

            active_plugin.console = console
            active_plugin.run()
        except Exception as e:
            console.print(f"[bold red]Headless Error:[/bold red] {e}")
        return

    console.print(
        Panel(
            "[bold blue]✨ Crisper: Universal Video Upscaler[/bold blue]", expand=False
        )
    )

    if args.input_vid and args.output_vid:
        run_upscale_flow(args, available_plugins)
        return

    while True:
        action = questionary.select(
            "Main Menu", choices=["🚀 Upscale a Video", "⚙️  Settings", "❌ Exit"]
        ).ask()

        if action == "🚀 Upscale a Video":
            run_upscale_flow(args, available_plugins)
        elif action == "⚙️  Settings":
            settings_menu()
        else:
            console.print("[dim]Exiting Crisper...[/dim]")
            sys.exit(0)


if __name__ == "__main__":
    main()
