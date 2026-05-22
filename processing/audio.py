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

    output_path = os.path.join(output_dir, "combined_audio.mp3")

    # Use filter_complex concat for reliable merging of different audio formats
    cmd = ["ffmpeg", "-y"]
    for fp in file_paths:
        cmd.extend(["-i", fp])

    filter_str = ""
    for i in range(len(file_paths)):
        filter_str += "[{}:a]".format(i)
    filter_str += "concat=n={}:v=0:a=1[outa]".format(len(file_paths))

    cmd.extend([
        "-filter_complex", filter_str,
        "-map", "[outa]",
        "-c:a", "libmp3lame", "-b:a", "192k",
        output_path
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Audio concat failed: " + result.stderr[-500:])
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
