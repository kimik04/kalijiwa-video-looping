document.addEventListener("DOMContentLoaded", () => {
    let videoFile = null;
    let audioFiles = [];
    let customIntroFile = null;
    let audioMode = "youtube";
    let introMode = "auto";
    let overlayLayers = [];
    let batchQueue = [];

    fetch("/api/default_overlay")
        .then(r => r.json())
        .then(data => {
            overlayLayers = data.layers;
            renderLayers();
        });

    // Tab switching
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const group = tab.parentElement;
            const section = group.parentElement;
            const tabName = tab.dataset.tab;

            group.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");

            section.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
            const target = section.querySelector(`#tab-${tabName}`);
            if (target) target.classList.add("active");

            if (tabName === "youtube" || tabName === "local") audioMode = tabName;
            if (tabName === "auto-intro" || tabName === "custom-intro") {
                introMode = tabName === "auto-intro" ? "auto" : "custom";
            }
        });
    });

    // File inputs
    document.getElementById("videoSource").addEventListener("change", (e) => {
        videoFile = e.target.files[0];
        document.getElementById("videoFileName").textContent = videoFile ? videoFile.name : "-";
    });

    document.getElementById("audioFiles").addEventListener("change", (e) => {
        audioFiles = Array.from(e.target.files);
        document.getElementById("audioFileNames").textContent = `${audioFiles.length} file(s)`;
        const list = document.getElementById("audioFileList");
        list.innerHTML = "";
        audioFiles.forEach(f => {
            const li = document.createElement("li");
            li.textContent = f.name;
            list.appendChild(li);
        });
    });

    document.getElementById("customIntro").addEventListener("change", (e) => {
        customIntroFile = e.target.files[0];
        document.getElementById("introFileName").textContent = customIntroFile ? customIntroFile.name : "-";
    });

    // Terminal log
    function logLine(msg, type = "") {
        const terminal = document.getElementById("terminalOutput");
        const line = document.createElement("div");
        line.className = "log-line" + (type ? " " + type : "");
        line.textContent = msg;
        terminal.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }

    document.getElementById("clearLog").addEventListener("click", () => {
        const terminal = document.getElementById("terminalOutput");
        terminal.innerHTML = '<div class="log-line dim">[ready] Kalijiwa Video Looping v1.0</div>';
    });

    // Overlay layers
    function renderLayers() {
        const container = document.getElementById("overlayLayers");
        container.innerHTML = "";
        overlayLayers.forEach((layer, idx) => {
            container.appendChild(createLayerCard(layer, idx));
        });
    }

    function createLayerCard(layer, idx) {
        const card = document.createElement("div");
        card.className = "layer-card";
        card.innerHTML = `
            <div class="layer-header">
                <span>Layer ${idx + 1}</span>
                <button class="btn btn-danger" data-idx="${idx}">x</button>
            </div>
            <div class="layer-grid">
                <div class="layer-field layer-field-full">
                    <label>Text</label>
                    <input type="text" data-idx="${idx}" data-key="text" value="${escapeHtml(layer.text)}">
                </div>
                <div class="layer-field">
                    <label>Font</label>
                    <input type="text" data-idx="${idx}" data-key="font" value="${layer.font}">
                </div>
                <div class="layer-field">
                    <label>Size</label>
                    <input type="number" data-idx="${idx}" data-key="fontsize" value="${layer.fontsize}">
                </div>
                <div class="layer-field">
                    <label>Color</label>
                    <input type="text" data-idx="${idx}" data-key="fontcolor" value="${layer.fontcolor}">
                </div>
                <div class="layer-field">
                    <label>X</label>
                    <input type="text" data-idx="${idx}" data-key="x" value="${layer.x}">
                </div>
                <div class="layer-field">
                    <label>Y</label>
                    <input type="text" data-idx="${idx}" data-key="y" value="${layer.y}">
                </div>
            </div>
            <div class="checkbox-row">
                <input type="checkbox" data-idx="${idx}" data-key="shadow" ${layer.shadow ? "checked" : ""}>
                <label>Shadow</label>
                <input type="checkbox" data-idx="${idx}" data-key="box" ${layer.box ? "checked" : ""}>
                <label>Box</label>
            </div>
            ${layer.box ? `
            <div class="layer-grid" style="margin-top:0.3rem">
                <div class="layer-field">
                    <label>Box Color</label>
                    <input type="text" data-idx="${idx}" data-key="boxcolor" value="${layer.boxcolor || ''}">
                </div>
                <div class="layer-field">
                    <label>Border</label>
                    <input type="number" data-idx="${idx}" data-key="boxborderw" value="${layer.boxborderw || 10}">
                </div>
            </div>` : ""}
            <div class="layer-timing">
                <div class="layer-field">
                    <label>In Start</label>
                    <input type="number" step="0.1" data-idx="${idx}" data-key="fade_in_start" value="${layer.fade_in_start}">
                </div>
                <div class="layer-field">
                    <label>In End</label>
                    <input type="number" step="0.1" data-idx="${idx}" data-key="fade_in_end" value="${layer.fade_in_end}">
                </div>
                <div class="layer-field">
                    <label>Out Start</label>
                    <input type="number" step="0.1" data-idx="${idx}" data-key="fade_out_start" value="${layer.fade_out_start}">
                </div>
                <div class="layer-field">
                    <label>Out End</label>
                    <input type="number" step="0.1" data-idx="${idx}" data-key="fade_out_end" value="${layer.fade_out_end}">
                </div>
            </div>
        `;

        card.querySelectorAll("input").forEach(input => {
            const key = input.dataset.key;
            const i = parseInt(input.dataset.idx);
            if (!key) return;
            input.addEventListener("change", () => {
                if (input.type === "checkbox") {
                    overlayLayers[i][key] = input.checked;
                    renderLayers();
                } else if (input.type === "number") {
                    overlayLayers[i][key] = parseFloat(input.value);
                } else {
                    overlayLayers[i][key] = input.value;
                }
            });
        });

        card.querySelector(".btn-danger").addEventListener("click", () => {
            overlayLayers.splice(idx, 1);
            renderLayers();
        });

        return card;
    }

    document.getElementById("addLayer").addEventListener("click", () => {
        overlayLayers.push({
            text: "New Text", font: "Avenir Next", fontsize: 30, fontcolor: "white",
            x: "(w-text_w)/2", y: "(h/2)", shadow: false, box: false,
            boxcolor: "black@0.5", boxborderw: 10,
            fade_in_start: 1, fade_in_end: 2, fade_out_start: 6, fade_out_end: 7,
        });
        renderLayers();
    });

    // Batch
    document.getElementById("addToBatch").addEventListener("click", () => {
        const item = buildPayloadPreview();
        if (!item) return;
        batchQueue.push(item);
        renderBatch();
        logLine(`[batch] Added item #${batchQueue.length}: ${item.label}`, "info");
    });

    document.getElementById("startBatch").addEventListener("click", async () => {
        if (batchQueue.length === 0) return;
        logLine(`[batch] Starting ${batchQueue.length} items...`, "info");

        for (let i = 0; i < batchQueue.length; i++) {
            const item = batchQueue[i];
            logLine(`[batch] Processing ${i+1}/${batchQueue.length}: ${item.label}`, "info");
            await runSingleJob(item);
        }
        batchQueue = [];
        renderBatch();
        logLine("[batch] All items complete", "success");
    });

    function renderBatch() {
        const section = document.getElementById("batchSection");
        const list = document.getElementById("batchList");
        const count = document.getElementById("batchCount");

        if (batchQueue.length === 0) {
            section.style.display = "none";
            return;
        }
        section.style.display = "block";
        count.textContent = batchQueue.length;
        list.innerHTML = "";
        batchQueue.forEach((item, i) => {
            const li = document.createElement("li");
            li.innerHTML = `<span>${item.label}</span><button class="btn btn-danger" onclick="removeBatch(${i})">x</button>`;
            list.appendChild(li);
        });
    }

    window.removeBatch = (i) => {
        batchQueue.splice(i, 1);
        renderBatch();
    };

    function buildPayloadPreview() {
        if (!videoFile) { alert("Select a video source."); return null; }
        if (audioMode === "youtube" && !document.getElementById("youtubeUrl").value.trim()) {
            alert("Enter a YouTube URL."); return null;
        }
        if (audioMode === "local" && audioFiles.length === 0) {
            alert("Select audio files."); return null;
        }
        if (introMode === "custom" && !customIntroFile) {
            alert("Select a custom intro."); return null;
        }

        const name = document.getElementById("outputName").value || "output";
        return {
            label: name,
            videoFile, audioFiles: [...audioFiles], customIntroFile,
            audioMode, introMode,
            youtubeUrl: document.getElementById("youtubeUrl").value.trim(),
            audioOrder: document.getElementById("audioOrder").value,
            bitrate: parseFloat(document.getElementById("bitrate").value),
            outputName: name,
            overlayLayers: JSON.parse(JSON.stringify(overlayLayers)),
            fade: {
                videoFadeIn: document.getElementById("videoFadeInEnabled").checked,
                videoFadeInDur: parseFloat(document.getElementById("videoFadeInDuration").value),
                videoFadeOut: document.getElementById("videoFadeOutEnabled").checked,
                videoFadeOutDur: parseFloat(document.getElementById("videoFadeOutDuration").value),
                audioFadeIn: document.getElementById("audioFadeInEnabled").checked,
                audioFadeInDur: parseFloat(document.getElementById("audioFadeInDuration").value),
                audioFadeOut: document.getElementById("audioFadeOutEnabled").checked,
                audioFadeOutDur: parseFloat(document.getElementById("audioFadeOutDuration").value),
            },
        };
    }

    // Single process
    document.getElementById("startProcess").addEventListener("click", async () => {
        const item = buildPayloadPreview();
        if (!item) return;
        await runSingleJob(item);
    });

    async function runSingleJob(item) {
        logLine(`[start] ${item.label}`, "info");

        try {
            logLine("[upload] Video source...", "dim");
            const videoPath = await uploadFile(item.videoFile);

            let audioFilePaths = [];
            if (item.audioMode === "local") {
                logLine(`[upload] ${item.audioFiles.length} audio file(s)...`, "dim");
                audioFilePaths = await uploadMultipleFiles(item.audioFiles);
            }

            let customIntroPath = null;
            if (item.introMode === "custom") {
                logLine("[upload] Custom intro...", "dim");
                customIntroPath = await uploadFile(item.customIntroFile);
            }

            const payload = {
                video_source: videoPath,
                audio_mode: item.audioMode,
                intro_mode: item.introMode,
                bitrate: item.bitrate,
                output_name: item.outputName,
            };

            if (item.audioMode === "youtube") {
                payload.youtube_url = item.youtubeUrl;
            } else {
                payload.audio_files = audioFilePaths;
                payload.audio_order = item.audioOrder;
            }

            if (item.introMode === "custom") {
                payload.custom_intro = customIntroPath;
            } else {
                payload.overlay_layers = item.overlayLayers;
            }

            logLine("[process] Sending to backend...", "dim");
            const res = await fetch("/api/process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const { job_id } = await res.json();

            await pollStatus(job_id);
        } catch (err) {
            logLine(`[error] ${err.message}`, "error");
        }
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        const data = await res.json();
        return data.path;
    }

    async function uploadMultipleFiles(files) {
        const formData = new FormData();
        files.forEach(f => formData.append("files", f));
        const res = await fetch("/api/upload_multi", { method: "POST", body: formData });
        const data = await res.json();
        return data.files.map(f => f.path);
    }

    function pollStatus(jobId) {
        return new Promise((resolve) => {
            let logIdx = 0;
            const interval = setInterval(async () => {
                const [statusRes, logsRes] = await Promise.all([
                    fetch(`/api/status/${jobId}`),
                    fetch(`/api/logs/${jobId}?since=${logIdx}`),
                ]);
                const status = await statusRes.json();
                const logsData = await logsRes.json();

                if (logsData.logs) {
                    logsData.logs.forEach(line => {
                        const type = line.includes("ERROR") ? "error" :
                                     line.includes("Done") ? "success" : "info";
                        logLine(line, type);
                    });
                    logIdx = logsData.total;
                }

                if (status.status === "done") {
                    clearInterval(interval);
                    const resultBar = document.getElementById("resultBar");
                    resultBar.classList.remove("hidden");
                    document.getElementById("downloadLink").href = `/api/download/${jobId}`;
                    resolve();
                } else if (status.status === "error") {
                    clearInterval(interval);
                    logLine(`[failed] ${status.error}`, "error");
                    resolve();
                }
            }, 1500);
        });
    }

    function escapeHtml(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
});
