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


def _run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + result.stderr[-500:])
    return result


def _bitrate_args(bitrate_mbps):
    return [
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", f"{bitrate_mbps}M",
        "-maxrate", f"{bitrate_mbps * 1.125:.1f}M",
        "-bufsize", f"{bitrate_mbps * 2}M",
    ]


def encode_base_loop(source_video, output_dir, bitrate_mbps=4,
                     trim_start=0, trim_end=0, crossfade_dur=0):
    output = os.path.join(output_dir, "base_loop.mp4")

    cmd = ["ffmpeg", "-y"]
    if trim_start > 0:
        cmd.extend(["-ss", str(trim_start)])
    cmd.extend(["-i", source_video])
    if trim_end > 0:
        cmd.extend(["-to", str(trim_end - trim_start)])

    cmd += _bitrate_args(bitrate_mbps) + ["-an", output]
    _run_ffmpeg(cmd)

    if crossfade_dur > 0:
        output = _apply_crossfade(output, output_dir, crossfade_dur, bitrate_mbps)

    return output


def _apply_crossfade(clip_path, output_dir, crossfade_dur, bitrate_mbps):
    output = os.path.join(output_dir, "base_loop_xfade.mp4")
    clip_dur = get_video_duration(clip_path)

    if crossfade_dur >= clip_dur * 0.5:
        crossfade_dur = clip_dur * 0.25

    offset = clip_dur - crossfade_dur

    cmd = [
        "ffmpeg", "-y",
        "-i", clip_path, "-i", clip_path,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={crossfade_dur}:offset={offset}[outv]",
        "-map", "[outv]",
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", f"{bitrate_mbps}M",
        "-an", output
    ]
    _run_ffmpeg(cmd)
    return output


def encode_intro_with_overlay(source_video, output_dir, layers, bitrate_mbps=4, fade_in_dur=0):
    output = os.path.join(output_dir, "intro_part.mp4")
    vf_parts = []
    if layers:
        vf_parts.append(build_drawtext_filter(layers))
    if fade_in_dur > 0:
        vf_parts.append(f"fade=t=in:st=0:d={fade_in_dur}")

    cmd = ["ffmpeg", "-y", "-i", source_video]
    if vf_parts:
        cmd.extend(["-vf", ",".join(vf_parts)])
    cmd += _bitrate_args(bitrate_mbps) + ["-an", output]
    _run_ffmpeg(cmd)
    return output


def encode_intro_with_fade_in(source_video, output_dir, fade_in_dur, bitrate_mbps=4):
    """Re-encode a custom intro video with fade in applied."""
    output = os.path.join(output_dir, "intro_faded.mp4")
    vf = f"fade=t=in:st=0:d={fade_in_dur}"
    cmd = ["ffmpeg", "-y", "-i", source_video, "-vf", vf] + _bitrate_args(bitrate_mbps) + ["-an", output]
    _run_ffmpeg(cmd)
    return output


def strip_audio(source_video, output_dir, bitrate_mbps=4):
    """Re-encode custom intro to strip audio track for concat compatibility."""
    output = os.path.join(output_dir, "intro_stripped.mp4")
    cmd = ["ffmpeg", "-y", "-i", source_video] + _bitrate_args(bitrate_mbps) + ["-an", output]
    _run_ffmpeg(cmd)
    return output


def encode_outro_with_fade_out(base_loop_path, output_dir, fade_out_dur, bitrate_mbps=4, target_dur=None):
    output = os.path.join(output_dir, "outro_part.mp4")
    loop_dur = get_video_duration(base_loop_path)
    if target_dur is None or target_dur <= 0 or target_dur > loop_dur:
        target_dur = loop_dur
    if fade_out_dur > target_dur:
        fade_out_dur = target_dur
    fade_start = max(0, target_dur - fade_out_dur)
    vf = f"fade=t=out:st={fade_start}:d={fade_out_dur}"
    cmd = [
        "ffmpeg", "-y", "-i", base_loop_path,
        "-t", f"{target_dur}", "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", f"{bitrate_mbps}M",
        "-an", output
    ]
    _run_ffmpeg(cmd)
    return output


def _build_audio_filter(audio_dur, fade_in_dur, fade_out_dur):
    parts = []
    if fade_in_dur and fade_in_dur > 0:
        parts.append(f"afade=t=in:st=0:d={fade_in_dur}")
    if fade_out_dur and fade_out_dur > 0:
        fade_start = max(0, audio_dur - fade_out_dur)
        parts.append(f"afade=t=out:st={fade_start}:d={fade_out_dur}")
    return ",".join(parts) if parts else None


def build_final_video(intro_path, base_loop_path, audio_path, output_path, temp_dir,
                      outro_path=None, loops_override=None,
                      audio_fade_in=0, audio_fade_out=0):
    from .audio import get_audio_duration

    audio_dur = get_audio_duration(audio_path)

    if loops_override is not None:
        loops_needed = loops_override
    else:
        intro_dur = get_video_duration(intro_path)
        loop_dur = get_video_duration(base_loop_path)
        if outro_path:
            outro_dur = get_video_duration(outro_path)
            loops_needed = max(0, math.ceil((audio_dur - intro_dur - outro_dur) / loop_dur))
        else:
            loops_needed = math.ceil((audio_dur - intro_dur) / loop_dur)

    concat_list = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list, "w") as f:
        if intro_path:
            f.write(f"file '{intro_path}'\n")
        for _ in range(loops_needed):
            f.write(f"file '{base_loop_path}'\n")
        if outro_path:
            f.write(f"file '{outro_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
    ]

    audio_filter = _build_audio_filter(audio_dur, audio_fade_in, audio_fade_out)
    if audio_filter:
        cmd.extend(["-af", audio_filter])

    cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest", output_path])

    _run_ffmpeg(cmd)
    os.remove(concat_list)
    return output_path


def build_final_with_custom_intro(custom_intro_path, base_loop_path, audio_path, output_path, temp_dir,
                                  outro_path=None, audio_fade_in=0, audio_fade_out=0):
    return build_final_video(
        custom_intro_path, base_loop_path, audio_path, output_path, temp_dir,
        outro_path=outro_path,
        audio_fade_in=audio_fade_in,
        audio_fade_out=audio_fade_out,
    )
