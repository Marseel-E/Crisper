__all__ = ["run_swarm"]

import os
import glob
import time
import subprocess
from rich.console import Console

console = Console()


def get_duration(input_vid: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_vid,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return float(result.stdout.strip())


def run_swarm(
    input_vid: str,
    output_vid: str,
    num_chunks: int,
    target_height: int,
    plugin_class_name: str,
    model_path: str = "",
    needs_tiling: bool = False,
) -> None:
    console.print(
        f"\n🐝 [bold yellow]Initializing Swarm Protocol: {num_chunks} Concurrent Nodes[/bold yellow]"
    )

    safe_name = os.path.basename(input_vid).replace(".", "_")
    swarm_dir = f"workspace_swarm_{safe_name}"

    if os.path.exists(swarm_dir):
        console.print("[dim]🧹 Cleaning up old swarm markers...[/dim]")
        for old_done in glob.glob(f"{swarm_dir}/*.done"):
            os.remove(old_done)

    os.makedirs(swarm_dir, exist_ok=True)

    duration = get_duration(input_vid)
    chunk_len = duration / num_chunks

    console.print(
        f"[cyan]Splitting master video into {num_chunks} precise chunks...[/cyan]"
    )

    source_chunks = []
    for i in range(num_chunks):
        start = i * chunk_len
        out_part = f"{swarm_dir}/source_{i:03d}.mp4"

        split_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_vid,
            "-ss",
            str(start),
            "-t",
            str(chunk_len),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "10",
            "-an",
            out_part,
            "-y",
        ]
        subprocess.run(split_cmd, check=True)
        source_chunks.append(out_part)

    console.print(f"[green]Successfully created {len(source_chunks)} nodes.[/green]")
    console.print("[cyan]Deploying Terminal Nodes...[/cyan]")

    cwd = os.getcwd()
    expected_outputs = []

    for i, chunk in enumerate(source_chunks):
        out_chunk = f"{swarm_dir}/upscaled_{i:03d}.mp4"
        expected_outputs.append(out_chunk)

        cmd = f'cd {cwd} && python3 . \\"{os.path.abspath(chunk)}\\" \\"{os.path.abspath(out_chunk)}\\" --headless --plugin \\"{plugin_class_name}\\" --height {target_height}'

        if model_path:
            cmd += f' --model_path \\"{model_path}\\"'
        if needs_tiling:
            cmd += f" --tiling"

        cmd += f' && touch \\"{os.path.abspath(out_chunk)}.done\\" && exit'

        apple_script: str = f"""
		tell application "Terminal"
			do script "{cmd}"
		end tell
		"""
        subprocess.run(["osascript", "-e", apple_script])

        time.sleep(1.5)

    console.print(
        "[bold magenta]Swarm deployed. Terminals are live. Waiting for nodes to report success...[/bold magenta]"
    )

    with console.status(
        "[bold yellow]Monitoring child terminals...", spinner="dots"
    ) as status:
        while True:
            completed = 0
            for out in expected_outputs:
                if os.path.exists(f"{out}.done"):
                    completed += 1

            status.update(
                f"[bold yellow]Monitoring child terminals... ({completed}/{num_chunks} Nodes Completed)"
            )

            if completed == num_chunks:
                break
            time.sleep(5)

    console.print(
        "\n✅ [bold green]All nodes completed. Commencing Final Stitching...[/bold green]"
    )

    concat_file = f"{swarm_dir}/concat.txt"
    with open(concat_file, "w") as f:
        for out in expected_outputs:
            f.write(f"file '{os.path.abspath(out)}'\n")

    temp_video = f"{swarm_dir}/welded_silent.mp4"

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

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            temp_video,
            "-i",
            input_vid,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0?",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            output_vid,
            "-y",
        ],
        check=True,
    )

    console.print(
        f"🎉 [bold green]Swarm Stitching Complete! Video saved to: {output_vid}[/bold green]"
    )
