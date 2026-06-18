#!/usr/bin/env python3
"""
Pi 2 — Display Node
====================
Ontvangt de geannoteerde videostream van Pi 1 via UDP/mpegts (FFmpeg)
en toont deze fullscreen op het scherm van de controller.

Geen ROS2 vereist op Pi 2 — puur FFmpeg + OpenCV.

Gebruik:
  python3 pi2_display_node.py
  python3 pi2_display_node.py --port 5000
  python3 pi2_display_node.py --port 5000 --ffmpeg /usr/bin/ffmpeg

Vereisten (Pi 2):
  pip install opencv-python numpy
  sudo apt install ffmpeg
"""

import argparse
import subprocess
import sys

import cv2
import numpy as np

# ============================================================
# === INSTELLINGEN ===========================================
# ============================================================

W, H        = 854, 480
FRAME_BYTES = W * H * 3
VENSTER     = "reCamera — Grijper"


# ============================================================
# === ARGUMENTEN =============================================
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Pi 2 display node")
    parser.add_argument("--port",   type=int, default=5000,
                        help="UDP poort waarop Pi 1 streamt (default: 5000)")
    parser.add_argument("--ffmpeg", type=str, default="ffmpeg",
                        help="Pad naar ffmpeg binary (default: ffmpeg)")
    return parser.parse_args()


# ============================================================
# === DISPLAY ================================================
# ============================================================

def run(port: int, ffmpeg_path: str):
    cmd = [
        ffmpeg_path,
        "-loglevel",  "error",
        "-fflags",    "nobuffer",
        "-flags",     "low_delay",
        "-i",         f"udp://0.0.0.0:{port}?overrun_nonfatal=1&fifo_size=50000000",
        "-f",         "rawvideo",
        "-pix_fmt",   "bgr24",
        "pipe:1",
    ]

    # Fullscreen venster klaarzetten
    cv2.namedWindow(VENSTER, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(VENSTER, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Wacht-scherm tonen zolang stream nog niet begonnen is
    wacht_frame = np.zeros((H, W, 3), dtype=np.uint8)
    cv2.putText(
        wacht_frame,
        f"Wachten op stream van Pi 1 (poort {port})...",
        (60, H // 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2,
    )
    cv2.imshow(VENSTER, wacht_frame)
    cv2.waitKey(1)

    print(f"Wachten op stream van Pi 1 op poort {port}...")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
    buf  = bytearray(FRAME_BYTES)
    mv   = memoryview(buf)

    gemiste_frames = 0

    try:
        while True:
            # ---- Frame lezen ----
            bytes_gelezen = 0
            while bytes_gelezen < FRAME_BYTES:
                n = proc.stdout.readinto(mv[bytes_gelezen:])
                if not n:
                    break
                bytes_gelezen += n

            # ---- Stream onderbroken ----
            if bytes_gelezen != FRAME_BYTES:
                gemiste_frames += 1
                status = np.zeros((H, W, 3), dtype=np.uint8)
                cv2.putText(
                    status,
                    f"Stream onderbroken — wachten... ({gemiste_frames}x)",
                    (60, H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 200), 2,
                )
                cv2.imshow(VENSTER, status)
                if cv2.waitKey(500) & 0xFF == ord("q"):
                    break
                continue

            gemiste_frames = 0

            # ---- Frame weergeven ----
            frame = np.frombuffer(buf, dtype=np.uint8).reshape((H, W, 3))
            cv2.imshow(VENSTER, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Gestopt door gebruiker.")
                break

    except KeyboardInterrupt:
        print("\nAfgesloten.")
    finally:
        proc.terminate()
        cv2.destroyAllWindows()


# ============================================================
# === ENTRY POINT ============================================
# ============================================================

if __name__ == "__main__":
    args = parse_args()
    run(port=args.port, ffmpeg_path=args.ffmpeg)