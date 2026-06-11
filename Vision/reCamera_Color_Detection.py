import cv2
import numpy as np
import threading
import subprocess
import os

# ============================================================
# === RECAMERA ===============================================
# ============================================================

RECAMERA_IP = "192.168.42.1"

_user = os.environ.get("RECAMERA_USER", "admin")
_pass = os.environ.get("RECAMERA_PASS", "admin")

RTSP_URL = f"rtsp://{_user}:{_pass}@{RECAMERA_IP}:554/live"

FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

TARGET_FPS = 30

# ============================================================
# === STREAM NAAR PI 2 =======================================
# ============================================================
PI2_IP   = "192.168.1.XX"   # ← Vul hier het statische IP van Pi 2 in
PI2_PORT = 5000

# ============================================================
# === HSV KLEUREN ============================================
# ============================================================

LOWER_RED1 = np.array([0, 100, 100])
UPPER_RED1 = np.array([10, 255, 255])

LOWER_RED2 = np.array([170, 100, 100])
UPPER_RED2 = np.array([180, 255, 255])

LOWER_GREEN = np.array([35, 50, 50])
UPPER_GREEN = np.array([85, 255, 255])

LOWER_WHITE = np.array([0, 0, 180])
UPPER_WHITE = np.array([180, 50, 255])

# ============================================================
# === RTSP STREAM ============================================
# ============================================================

class RTSPStream:

    OUT_W = 854
    OUT_H = 480
    FRAME_BYTES = OUT_W * OUT_H * 3

    def __init__(self, url):
        self.url = url
        self.frame = None
        self.lock = threading.Lock()
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(
            target=self._read_loop,
            daemon=True
        ).start()

    def _read_loop(self):
        cmd = [
            FFMPEG_PATH,
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-analyzeduration", "1000000",
            "-probesize", "1000000",
            "-i", self.url,
            "-vf", f"fps={TARGET_FPS},scale={self.OUT_W}:{self.OUT_H}",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "pipe:1",
        ]

        print("FFmpeg gestart")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )

        buf = bytearray(self.FRAME_BYTES)
        mv = memoryview(buf)

        while self.running:
            bytes_gelezen = 0

            while bytes_gelezen < self.FRAME_BYTES:
                n = proc.stdout.readinto(mv[bytes_gelezen:])
                if not n:
                    break
                bytes_gelezen += n

            if bytes_gelezen != self.FRAME_BYTES:
                continue

            frame = np.frombuffer(buf, dtype=np.uint8).reshape(
                (self.OUT_H, self.OUT_W, 3)
            ).copy()

            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False


# ============================================================
# === FRAME STREAMER NAAR PI 2 ===============================
# ============================================================

class FrameStreamer:
    def __init__(self, doel_ip, doel_port, breedte, hoogte, fps):
        self.doel_ip   = doel_ip
        self.doel_port = doel_port
        self.breedte   = breedte
        self.hoogte    = hoogte
        self.fps       = fps
        self._proc     = None
        self._lock     = threading.Lock()

    def start(self):
        cmd = [
            FFMPEG_PATH,
            "-loglevel",   "error",
            "-f",          "rawvideo",
            "-pix_fmt",    "bgr24",
            "-s",          f"{self.breedte}x{self.hoogte}",
            "-r",          str(self.fps),
            "-i",          "pipe:0",
            "-c:v",        "libx264",
            "-preset",     "ultrafast",
            "-tune",       "zerolatency",
            "-f",          "mpegts",
            f"udp://{self.doel_ip}:{self.doel_port}?pkt_size=1316",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        print(f"Stream gestart naar {self.doel_ip}:{self.doel_port}")

    def stuur_frame(self, frame):
        if self._proc is None or self._proc.poll() is not None:
            print("Streamer gestopt, herstart...")
            self.start()
        try:
            with self._lock:
                self._proc.stdin.write(frame.tobytes())
        except Exception as e:
            print(f"Stream fout: {e}")

    def stop(self):
        if self._proc:
            try:
                self._proc.stdin.close()
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass
            self._proc = None


# ============================================================
# === KLEURDETECTIE ==========================================
# ============================================================

def teken_kleur(frame, mask, kleur, naam):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 500:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(frame, (x, y), (x + w, y + h), kleur, 2)
        cv2.putText(frame, naam, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, kleur, 2)


# ============================================================
# === MAIN ===================================================
# ============================================================

if __name__ == "__main__":

    print("Verbinden met reCamera...")

    stream   = RTSPStream(RTSP_URL)
    streamer = FrameStreamer(PI2_IP, PI2_PORT, RTSPStream.OUT_W, RTSPStream.OUT_H, TARGET_FPS)

    stream.start()
    streamer.start()

    kernel = np.ones((5, 5), np.uint8)

    try:
        while True:
            frame = stream.read()
            if frame is None:
                continue

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Maskers aanmaken
            mask_red = cv2.bitwise_or(
                cv2.inRange(hsv, LOWER_RED1, UPPER_RED1),
                cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
            )
            mask_green = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
            mask_white = cv2.inRange(hsv, LOWER_WHITE, UPPER_WHITE)

            # Morfologie toepassen
            mask_red   = cv2.morphologyEx(mask_red,   cv2.MORPH_OPEN, kernel)
            mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)
            mask_white = cv2.morphologyEx(mask_white, cv2.MORPH_OPEN, kernel)

            # Tekenen op frame
            teken_kleur(frame, mask_red,   (0, 0, 255),     "ROOD")
            teken_kleur(frame, mask_green, (0, 255, 0),     "GROEN")
            teken_kleur(frame, mask_white, (255, 255, 255), "WIT")

            # Verstuur verwerkt frame naar Pi 2
            streamer.stuur_frame(frame)

            cv2.imshow("reCamera", frame)
            cv2.imshow("Rood",  mask_red)
            cv2.imshow("Groen", mask_green)
            cv2.imshow("Wit",   mask_white)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        streamer.stop()
        stream.stop()
        cv2.destroyAllWindows()