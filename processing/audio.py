import os
import subprocess
import random
import json


def download_youtube_audio(url, output_dir):
    output_path = os.path.join(output_dir, "yt_audio.mp3")
    cmd = [
        "yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3",
        "-o", output_path.replace(".mp3", ".%(ext)s"),
        url
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def concat_local_audio(file_paths, output_dir, mode="sequential"):
    if mode == "random":
        file_paths = file_paths[:]
        random.shuffle(file_paths)

    list_path = os.path.join(output_dir, "audio_concat.txt")
    with open(list_path, "w") as f:
        for fp in file_paths:
            safe_path = fp.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    output_path = os.path.join(output_dir, "combined_audio.mp3")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    os.remove(list_path)
    return output_path


def get_audio_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])
