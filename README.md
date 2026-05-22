# Kalijiwa Video Looping

Dashboard web untuk membuat video looping dengan intro animasi dan musik. Proses encoding cepat menggunakan teknik stream-copy (hanya intro yang di-re-encode, sisanya copy langsung).

## Fitur

- **Video Source** — Pilih video lokal sebagai base loop dan intro
- **Audio Source** — Download dari YouTube (yt-dlp) atau gabung file audio lokal (urut/acak)
- **Intro Mode** — Auto-generate dengan text overlay editor atau upload video intro custom
- **Text Overlay Editor** — Edit teks, font, warna, posisi, timing fade in/out, shadow, box background
- **Batch Processing** — Antri beberapa project, proses otomatis berurutan
- **Terminal Log** — Monitoring real-time setiap tahap proses
- **Target Bitrate** — Kontrol ukuran output (~2GB/jam pada 4 Mbps)

## Cara Kerja

1. Encode base loop sekali saja di bitrate rendah (cepat, ~4MB per 8 detik)
2. Encode intro dengan text overlay (sekali, 8 detik)
3. Concat intro + loop berulang menggunakan stream copy (tanpa re-encode, sangat cepat)
4. Tambahkan audio sebagai track terpisah

## Kebutuhan Sistem

- Python 3.9+
- ffmpeg & ffprobe
- yt-dlp (untuk fitur download audio YouTube)

## Instalasi

```bash
cd LoopingVideoApp
/Library/Developer/CommandLineTools/usr/bin/python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Menjalankan

```bash
./venv/bin/python3 app.py
```

Buka browser di `http://localhost:5555`

## Struktur Project

```
LoopingVideoApp/
├── app.py                 # Flask server utama
├── requirements.txt       # Dependencies
├── processing/
│   ├── audio.py           # Download YouTube, concat audio lokal
│   ├── video.py           # Encode intro, loop, final merge
│   └── overlay.py         # Generate ffmpeg drawtext filter
├── static/
│   ├── css/style.css      # Styling dashboard
│   └── js/app.js          # Frontend logic
├── templates/
│   └── index.html         # Dashboard UI
├── uploads/               # File upload sementara
├── output/                # Hasil video final
└── temp/                  # File proses sementara
```

## Penggunaan

### Mode Single

1. Pilih video source (file .mp4 pendek untuk di-loop)
2. Pilih audio: masukkan link YouTube atau pilih file audio lokal
3. Pilih intro: auto-generate (edit overlay di panel tengah) atau upload video intro custom
4. Atur nama output dan bitrate
5. Klik **Start**

### Mode Batch

1. Isi konfigurasi seperti mode single
2. Klik **+ Batch** untuk menambah ke antrian
3. Ulangi untuk project lain
4. Klik **Run Batch** untuk proses semua berurutan

### Text Overlay Editor

Setiap layer bisa diatur:
- **Text** — Isi teks (nama channel, subscribe, dll)
- **Font** — Nama font sistem (Avenir Next, Helvetica, Arial, dll)
- **Size** — Ukuran font
- **Color** — Warna teks (white, red, #ffffff, dll)
- **X/Y** — Posisi (gunakan expression ffmpeg seperti `(w-text_w)/2`)
- **Shadow** — Bayangan teks
- **Box** — Background kotak di belakang teks
- **Timing** — Fade in start/end dan fade out start/end (dalam detik)

## Estimasi Ukuran Output

| Bitrate | Durasi 1 Jam | Kualitas |
|---------|-------------|----------|
| 2 Mbps  | ~1 GB       | Cukup untuk scene statis |
| 4 Mbps  | ~2 GB       | Bagus untuk 1080p |
| 8 Mbps  | ~4 GB       | Sangat bagus |

## Lisensi

MIT
