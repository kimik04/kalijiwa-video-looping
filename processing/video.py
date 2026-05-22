import os
import math
import subprocess
import json

from .overlay import build_drawtext_filter


def get_video_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def encode_base_loop(source_video, output_dir, bitrate_mbps=4):
    output = os.path.join(output_dir, "base_loop.mp4")
    bitrate = f"{bitrate_mbps}M"
    maxrate = f"{bitrate_mbps * 1.125:.1f}M"
    bufsize = f"{bitrate_mbps * 2}M"

    cmd = [
        "ffmpeg", "-y",
        "-i", source_video,
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize,
        "-profile:v", "high", "-r", "24",
        "-an", output
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output


def encode_intro_with_overlay(source_video, output_dir, layers, bitrate_mbps=4):
    output = os.path.join(output_dir, "intro_part.mp4")
    vf = build_drawtext_filter(layers)
    bitrate = f"{bitrate_mbps}M"
    maxrate = f"{bitrate_mbps * 1.125:.1f}M"
    bufsize = f"{bitrate_mbps * 2}M"

    cmd = [
        "ffmpeg", "-y",
        "-i", source_video,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize,
        "-profile:v", "high", "-r", "24",
        "-an", output
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output


def build_final_video(intro_path, base_loop_path, audio_path, output_path, temp_dir):
    from .audio import get_audio_duration

    audio_dur = get_audio_duration(audio_path)
    intro_dur = get_video_duration(intro_path)
    remaining = audio_dur - intro_dur
    loop_dur = get_video_duration(base_loop_path)
    loops_needed = math.ceil(remaining / loop_dur)

    concat_list = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{intro_path}'\n")
        for _ in range(loops_needed):
            f.write(f"file '{base_loop_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.remove(concat_list)
    return output_path


def build_final_with_custom_intro(custom_intro_path, base_loop_path, audio_path, output_path, temp_dir):
    """Use a pre-made intro video file instead of generating one."""
    from .audio import get_audio_duration

    audio_dur = get_audio_duration(audio_path)
    intro_dur = get_video_duration(custom_intro_path)
    remaining = audio_dur - intro_dur
    loop_dur = get_video_duration(base_loop_path)
    loops_needed = math.ceil(remaining / loop_dur)

    concat_list = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{custom_intro_path}'\n")
        for _ in range(loops_needed):
            f.write(f"file '{base_loop_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.remove(concat_list)
    return output_path
