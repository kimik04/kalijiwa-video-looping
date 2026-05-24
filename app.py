import os
import uuid
import time
import threading
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from processing.audio import download_youtube_audio, concat_local_audio, get_audio_duration
from processing.video import (
    encode_base_loop, encode_intro_with_overlay,
    encode_intro_with_fade_in, encode_outro_with_fade_out,
    build_final_video, get_video_duration
)
from processing.overlay import default_layers

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["OUTPUT_FOLDER"] = os.path.join(os.path.dirname(__file__), "output")
app.config["TEMP_FOLDER"] = os.path.join(os.path.dirname(__file__), "temp")

jobs = {}


def _log(job_id, msg):
    if job_id in jobs:
        ts = time.strftime("%H:%M:%S")
        jobs[job_id]["logs"].append(f"[{ts}] {msg}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No filename"}), 400
    filename = secure_filename(f.filename)
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(app.config["UPLOAD_FOLDER"], job_id)
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, filename)
    f.save(path)
    return jsonify({"path": path, "filename": filename, "job_id": job_id})


@app.route("/api/upload_multi", methods=["POST"])
def upload_multi():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files"}), 400
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(app.config["UPLOAD_FOLDER"], job_id)
    os.makedirs(job_dir, exist_ok=True)
    paths = []
    for f in files:
        filename = secure_filename(f.filename)
        path = os.path.join(job_dir, filename)
        f.save(path)
        paths.append({"path": path, "filename": filename})
    return jsonify({"files": paths, "job_id": job_id})


@app.route("/api/default_overlay")
def get_default_overlay():
    return jsonify({"layers": default_layers()})


@app.route("/api/process", methods=["POST"])
def process_video():
    data = request.get_json()
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "processing",
        "progress": "",
        "error": None,
        "output": None,
        "logs": [],
    }
    t = threading.Thread(target=_run_job, args=(job_id, data))
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/batch", methods=["POST"])
def batch_process():
    data = request.get_json()
    items = data.get("items", [])
    batch_id = str(uuid.uuid4())[:8]
    job_ids = []
    for item in items:
        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "status": "queued",
            "progress": "",
            "error": None,
            "output": None,
            "logs": [],
            "batch_id": batch_id,
        }
        job_ids.append(job_id)

    t = threading.Thread(target=_run_batch, args=(job_ids, items))
    t.start()
    return jsonify({"batch_id": batch_id, "job_ids": job_ids})


@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/logs/<job_id>")
def job_logs(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    since = int(request.args.get("since", 0))
    return jsonify({"logs": job["logs"][since:], "total": len(job["logs"])})


@app.route("/api/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("output"):
        return jsonify({"error": "Not ready"}), 404
    directory = os.path.dirname(job["output"])
    filename = os.path.basename(job["output"])
    return send_from_directory(directory, filename, as_attachment=True)


def _run_batch(job_ids, items):
    for i, (job_id, data) in enumerate(zip(job_ids, items)):
        jobs[job_id]["status"] = "processing"
        _log(job_id, f"Starting batch item {i+1}/{len(items)}")
        _run_job(job_id, data)


def _run_job(job_id, data):
    try:
        temp_dir = os.path.join(app.config["TEMP_FOLDER"], job_id)
        os.makedirs(temp_dir, exist_ok=True)

        video_source = data["video_source"]
        audio_mode = data["audio_mode"]
        intro_mode = data["intro_mode"]
        bitrate = data.get("bitrate", 4)
        fade = data.get("fade", {}) or {}

        v_fade_in = float(fade.get("videoFadeInDur", 0)) if fade.get("videoFadeIn") else 0
        v_fade_out = float(fade.get("videoFadeOutDur", 0)) if fade.get("videoFadeOut") else 0
        a_fade_in = float(fade.get("audioFadeInDur", 0)) if fade.get("audioFadeIn") else 0
        a_fade_out = float(fade.get("audioFadeOutDur", 0)) if fade.get("audioFadeOut") else 0

        _log(job_id, f"Video: {os.path.basename(video_source)}")
        _log(job_id, f"Audio mode: {audio_mode} | Intro: {intro_mode} | Bitrate: {bitrate}M")
        if v_fade_in or v_fade_out or a_fade_in or a_fade_out:
            _log(job_id, f"Fade — video in:{v_fade_in}s out:{v_fade_out}s | audio in:{a_fade_in}s out:{a_fade_out}s")

        # Step 1: Prepare audio
        jobs[job_id]["progress"] = "Preparing audio..."
        if audio_mode == "youtube":
            _log(job_id, f"Downloading from YouTube: {data['youtube_url']}")
            audio_path = download_youtube_audio(data["youtube_url"], temp_dir)
            _log(job_id, "Audio download complete")
        else:
            file_paths = data["audio_files"]
            order = data.get("audio_order", "sequential")
            _log(job_id, f"Local audio: {len(file_paths)} file(s), order={order}")
            if len(file_paths) == 1:
                audio_path = file_paths[0]
            else:
                audio_path = concat_local_audio(file_paths, temp_dir, mode=order)
            _log(job_id, "Audio prepared")

        audio_dur = get_audio_duration(audio_path)
        _log(job_id, f"Audio duration: {int(audio_dur//60)}m {int(audio_dur%60)}s")

        # Step 2: Encode base loop
        jobs[job_id]["progress"] = "Encoding base loop..."
        _log(job_id, f"Encoding base loop @ {bitrate} Mbps...")
        base_loop = encode_base_loop(video_source, temp_dir, bitrate_mbps=bitrate)
        loop_size = os.path.getsize(base_loop) / (1024*1024)
        loop_dur = get_video_duration(base_loop)
        _log(job_id, f"Base loop: {loop_size:.1f} MB ({loop_dur:.1f}s)")

        # Cap fade durations to segment length
        if v_fade_in and v_fade_in > loop_dur:
            _log(job_id, f"WARN: video fade in capped {v_fade_in}s -> {loop_dur}s")
            v_fade_in = loop_dur
        if v_fade_out and v_fade_out > loop_dur:
            _log(job_id, f"WARN: video fade out capped {v_fade_out}s -> {loop_dur}s")
            v_fade_out = loop_dur

        # Step 3: Prepare intro (with optional fade in)
        jobs[job_id]["progress"] = "Preparing intro..."
        if intro_mode == "custom":
            intro_src = data["custom_intro"]
            if v_fade_in > 0:
                _log(job_id, f"Re-encoding custom intro with fade in {v_fade_in}s...")
                intro_path = encode_intro_with_fade_in(intro_src, temp_dir, v_fade_in, bitrate_mbps=bitrate)
            else:
                intro_path = intro_src
                _log(job_id, f"Using custom intro: {os.path.basename(intro_path)}")
        else:
            layers = data.get("overlay_layers", default_layers())
            _log(job_id, f"Generating intro with {len(layers)} overlay layers...")
            intro_path = encode_intro_with_overlay(
                video_source, temp_dir, layers, bitrate_mbps=bitrate, fade_in_dur=v_fade_in
            )
            _log(job_id, "Intro encoded")

        intro_dur = get_video_duration(intro_path)

        outro_path = None
        outro_dur = 0
        import math
        if v_fade_out > 0:
            remaining = audio_dur - intro_dur
            loops = max(0, math.floor((remaining - v_fade_out) / loop_dur))
            outro_dur = remaining - loops * loop_dur
            if outro_dur < v_fade_out:
                outro_dur = v_fade_out
            _log(job_id, f"Encoding outro {outro_dur:.2f}s with fade out {v_fade_out}s...")
            outro_path = encode_outro_with_fade_out(
                base_loop, temp_dir, v_fade_out, bitrate_mbps=bitrate, target_dur=outro_dur
            )
            outro_dur = get_video_duration(outro_path)
            _log(job_id, "Outro encoded")
        else:
            loops = max(0, math.ceil((audio_dur - intro_dur) / loop_dur))

        jobs[job_id]["progress"] = "Building final video..."
        output_name = data.get("output_name", "output") + ".mp4"
        output_path = os.path.join(app.config["OUTPUT_FOLDER"], f"{job_id}_{output_name}")

        est_size = (loop_size * (loops + 2) + audio_dur * 192 / 8 / 1024) / 1024
        _log(job_id, f"Concat: intro + {loops} loops" + (" + outro" if outro_path else "") + f" | Est. size: {est_size:.2f} GB")
        _log(job_id, "Stream copying (no re-encode)...")

        build_final_video(
            intro_path, base_loop, audio_path, output_path, temp_dir,
            outro_path=outro_path,
            loops_override=loops,
            audio_fade_in=a_fade_in,
            audio_fade_out=a_fade_out,
        )

        final_size = os.path.getsize(output_path) / (1024*1024*1024)
        _log(job_id, f"Done! Output: {final_size:.2f} GB")

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        jobs[job_id]["status"] = "done"
        jobs[job_id]["progress"] = "Complete"
        jobs[job_id]["output"] = output_path
        _log(job_id, f"Saved: {os.path.basename(output_path)}")

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        _log(job_id, f"ERROR: {str(e)}")


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_FOLDER"], exist_ok=True)
    app.run(debug=True, port=5555)
