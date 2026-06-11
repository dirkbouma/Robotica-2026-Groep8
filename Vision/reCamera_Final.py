import numpy as np
import cv2
import threading
import time
import socket
import math
import subprocess
import os
from dataclasses import dataclass

# ============================================================
# === RECAMERA INSTELLINGEN ==================================
# ============================================================
RECAMERA_IP = "192.168.42.1"

_user = os.environ.get("RECAMERA_USER", "admin")
_pass = os.environ.get("RECAMERA_PASS", "admin")
RTSP_URL = f"rtsp://{_user}:{_pass}@{RECAMERA_IP}:554/live"

FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_BACKOFF      = 2.0

# ============================================================
# === SOCKET INSTELLINGEN ====================================
# ============================================================
ROS_IP   = "127.0.0.1"
ROS_PORT = 5005

# ============================================================
# === STREAM NAAR PI 2 =======================================
# ============================================================
PI2_IP   = "192.168.1.XX"   # ← Vul hier het statische IP van Pi 2 in
PI2_PORT = 5000

# ============================================================
# === FRAME-RATE BEGRENZING ==================================
# ============================================================
TARGET_FPS = 30

# ============================================================
# === DETECTIE-PARAMETERS ====================================
# ============================================================
@dataclass
class DetectieParams:
    min_area:        int
    max_area:        int
    min_aspect:      float
    max_aspect:      float
    min_circularity: float
    min_solidity:    float
    min_color_ratio: float

RIJP_PARAMS = DetectieParams(
    min_area        = 500,
    max_area        = 50000,
    min_aspect      = 0.2,
    max_aspect      = 1.8,
    min_circularity = 0.35,
    min_solidity    = 0.65,
    min_color_ratio = 0.65,
)

ONRIJP_PARAMS = DetectieParams(
    min_area        = 1200,
    max_area        = 15000,
    min_aspect      = 0.42,
    max_aspect      = 1.6,
    min_circularity = 0.25,
    min_solidity    = 0.60,
    min_color_ratio = 0.55,
)

# ============================================================
# === BEWEGINGSRICHTING INSTELLINGEN =========================
# ============================================================
SCHIJF_MIDDELPUNT = (427, 240)
DEBUG_SCHIJF      = False
MIN_HOEK_DELTA    = 0.8
MIN_RADIUS_SCHIJF = 30
POSITION_GRID     = 40
DEBUG             = False

# ============================================================
# === DIEPTE-SCHATTING INSTELLINGEN ==========================
# ============================================================
ECHTE_DIAMETER_MM = 40
FOCAL_LENGTH_PX   = 600
TAFEL_Z_MM        = 350
MIN_RADIUS_DIEPTE = 8
DIEPTE_MAX_MM     = 1500

# ============================================================
# === HSV-KLEURDREMPELS ======================================
# ============================================================

# Rijpe aardbei (rood)
lower_red1 = np.array([0,   150, 100])
upper_red1 = np.array([8,   255, 255])
lower_red2 = np.array([172, 150, 100])
upper_red2 = np.array([180, 255, 255])

# Onrijpe aardbei — lichaam (lichtblauw/grijs-blauw)
lower_unripe_blauw = np.array([88,  35,  60])
upper_unripe_blauw = np.array([108, 110, 190])

# Onrijpe aardbei — blad (donkergroen)
lower_unripe_groen = np.array([55,  60,  25])
upper_unripe_groen = np.array([80,  200, 120])

# ============================================================
# === MORPHOLOGIE-KERNELS ====================================
# ============================================================
KERNEL_SMALL  = np.ones((3, 3), np.uint8)
KERNEL_MEDIUM = np.ones((5, 5), np.uint8)

# ============================================================
# === VISUALISATIE-KLEUREN ===================================
# ============================================================
COLOR_RIPE   = (0, 255,   0)
COLOR_UNRIPE = (0, 165, 255)
COLOR_TEXT   = (255, 255, 255)


# ============================================================
# === RTSP-STREAM ============================================
# ============================================================

class RTSPStream:
    OUT_W       = 854
    OUT_H       = 480
    FRAME_BYTES = OUT_W * OUT_H * 3

    def __init__(self, url):
        self.url          = url
        self.frame        = None
        self.frame_id     = 0
        self.lock         = threading.Lock()
        self._frame_event = threading.Event()
        self.running      = False
        self._proc        = None
        self.reconnect_attempts = 0

    def start(self):
        self.running = True
        self.thread  = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _spawn(self):
        self._kill()
        cmd = [
            FFMPEG_PATH,
            "-loglevel",        "error",
            "-rtsp_transport",  "tcp",
            "-fflags",          "nobuffer",
            "-flags",           "low_delay",
            "-analyzeduration", "1000000",
            "-probesize",       "1000000",
            "-i",               self.url,
            "-vf",              f"fps={TARGET_FPS},scale={self.OUT_W}:{self.OUT_H}",
            "-f",               "rawvideo",
            "-pix_fmt",         "bgr24",
            "pipe:1",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

    def _kill(self):
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def _read_loop(self):
        buf = bytearray(self.FRAME_BYTES)
        mv  = memoryview(buf)

        self._spawn()
        while self.running:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                self.reconnect_attempts += 1
                if (MAX_RECONNECT_ATTEMPTS is not None
                        and self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS):
                    print(f"Maximaal aantal herverbindingspogingen "
                          f"({MAX_RECONNECT_ATTEMPTS}) bereikt. Stoppen.")
                    self.running = False
                    break
                print(f"Herverbinden (poging {self.reconnect_attempts})...")
                time.sleep(RECONNECT_BACKOFF)
                self._spawn()
                continue

            bytes_gelezen = 0
            try:
                while bytes_gelezen < self.FRAME_BYTES:
                    n = proc.stdout.readinto(mv[bytes_gelezen:])
                    if not n:
                        break
                    bytes_gelezen += n
            except Exception as e:
                print(f"Leesfout: {e}")
                bytes_gelezen = 0

            if bytes_gelezen != self.FRAME_BYTES:
                if self._proc and self._proc.poll() is not None:
                    print("FFmpeg gestopt, herverbinden...")
                    time.sleep(1)
                    self._spawn()
                continue

            frame = np.frombuffer(buf, dtype=np.uint8).reshape(
                (self.OUT_H, self.OUT_W, 3)
            ).copy()

            with self.lock:
                self.frame    = frame
                self.frame_id += 1
            self._frame_event.set()
            self.reconnect_attempts = 0

    def read(self, last_seen_id=None, timeout=0.1):
        if last_seen_id is not None:
            with self.lock:
                current_id = self.frame_id
            if current_id == last_seen_id:
                self._frame_event.wait(timeout)
                self._frame_event.clear()

        with self.lock:
            if self.frame is not None:
                return self.frame_id, self.frame.copy()
            return None, None

    def is_ready(self):
        with self.lock:
            return self.frame is not None

    def stop(self):
        self.running = False
        self._frame_event.set()
        self._kill()


# ============================================================
# === FRAME STREAMER NAAR PI 2 ===============================
# ============================================================

class FrameStreamer:
    """
    Stuurt verwerkte frames via FFmpeg als UDP/mpegts stream naar Pi 2.
    Lage latency door ultrafast preset + zerolatency tune.
    """
    def __init__(self, doel_ip, doel_port, breedte, hoogte, fps):
        self.doel_ip  = doel_ip
        self.doel_port = doel_port
        self.breedte  = breedte
        self.hoogte   = hoogte
        self.fps      = fps
        self._proc    = None
        self._lock    = threading.Lock()

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
# === MASKER-HELPERS =========================================
# ============================================================

def maak_rood_masker(hsv):
    m1 = cv2.inRange(hsv, lower_red1, upper_red1)
    m2 = cv2.inRange(hsv, lower_red2, upper_red2)
    return cv2.bitwise_or(m1, m2)


def maak_onrijp_masker(hsv):
    masker_blauw = cv2.inRange(hsv, lower_unripe_blauw, upper_unripe_blauw)
    masker_groen = cv2.inRange(hsv, lower_unripe_groen, upper_unripe_groen)

    # Groen alleen meenemen als het dicht bij blauw zit (blaadje van aardbei)
    blauw_vergroot = cv2.dilate(masker_blauw, np.ones((30, 30), np.uint8))
    masker_groen   = cv2.bitwise_and(masker_groen, blauw_vergroot)

    return cv2.bitwise_or(masker_blauw, masker_groen)


def pas_morfologie_toe(masker, agressief=False):
    masker = cv2.morphologyEx(masker, cv2.MORPH_OPEN,  KERNEL_SMALL)
    masker = cv2.morphologyEx(masker, cv2.MORPH_CLOSE, KERNEL_MEDIUM)
    if agressief:
        masker = cv2.morphologyEx(masker, cv2.MORPH_ERODE,  KERNEL_SMALL)
        masker = cv2.morphologyEx(masker, cv2.MORPH_DILATE, KERNEL_MEDIUM)
    return masker


# ============================================================
# === DIEPTE-SCHATTING =======================================
# ============================================================

def schat_diepte_mm(radius_px: int) -> tuple[float, str]:
    if radius_px >= MIN_RADIUS_DIEPTE:
        z = (ECHTE_DIAMETER_MM * FOCAL_LENGTH_PX) / (2 * radius_px)
        if z <= DIEPTE_MAX_MM:
            return round(z, 1), "grootte"
    return float(TAFEL_Z_MM), "tafel"


# ============================================================
# === DETECTIE ===============================================
# ============================================================

def _kleur_ratio(masker, contour):
    x, y, w, h = cv2.boundingRect(contour)
    roi_masker  = masker[y:y + h, x:x + w]
    roi_cnt     = np.zeros((h, w), np.uint8)
    shifted_contour = contour - np.array([x, y])
    cv2.drawContours(roi_cnt, [shifted_contour], -1, 255, cv2.FILLED)
    kleur  = cv2.countNonZero(cv2.bitwise_and(roi_masker, roi_cnt))
    totaal = cv2.countNonZero(roi_cnt)
    return kleur / totaal if totaal > 0 else 0.0


def detecteer_aardbeien(masker, rijp: bool):
    p     = RIJP_PARAMS if rijp else ONRIJP_PARAMS
    label = "RIJP"      if rijp else "ONRIJP"

    contours, _ = cv2.findContours(masker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    resultaten  = []
    ruis_teller = 0
    ruis_max    = 0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < p.min_area:
            ruis_teller += 1
            ruis_max = max(ruis_max, area)
            continue
        if area > p.max_area:
            if DEBUG:
                print(f"[{label}] Afgewezen: te groot ({area:.0f} px)")
            continue

        x, y, w, h = cv2.boundingRect(contour)
        ar = w / h
        if not (p.min_aspect <= ar <= p.max_aspect):
            if DEBUG:
                print(f"[{label}] Afgewezen aspect ratio: {ar:.2f}  "
                      f"(area={area:.0f}, bbox={w}x{h})")
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / perimeter ** 2
        if circularity < p.min_circularity:
            if DEBUG:
                print(f"[{label}] Afgewezen circulariteit: {circularity:.2f}  "
                      f"(area={area:.0f}, drempel={p.min_circularity})")
            continue

        hull_area = cv2.contourArea(cv2.convexHull(contour))
        solidity  = area / hull_area if hull_area > 0 else 0
        if solidity < p.min_solidity:
            if DEBUG:
                print(f"[{label}] Afgewezen solidity: {solidity:.2f}  "
                      f"(area={area:.0f}, drempel={p.min_solidity})")
            continue

        kleur_ratio = _kleur_ratio(masker, contour)
        if kleur_ratio < p.min_color_ratio:
            if DEBUG:
                print(f"[{label}] Afgewezen kleurverhouding: {kleur_ratio:.2f}  "
                      f"(area={area:.0f}, drempel={p.min_color_ratio})")
            continue

        if DEBUG:
            print(f"[{label}] ✓ GEDETECTEERD  area={area:.0f}, "
                  f"AR={ar:.2f}, circ={circularity:.2f}, "
                  f"solid={solidity:.2f}, kleur={kleur_ratio:.0%}")

        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        r_int = int(radius)

        if rijp:
            z_mm, z_methode = schat_diepte_mm(r_int)
        else:
            z_mm, z_methode = float(TAFEL_Z_MM), "tafel"

        resultaten.append({
            "cx":          int(cx),
            "cy":          int(cy),
            "x":           x, "y": y, "w": w, "h": h,
            "radius":      r_int,
            "kleur_ratio": kleur_ratio,
            "rijp":        rijp,
            "z_mm":        z_mm,
            "z_methode":   z_methode,
        })

    if DEBUG and ruis_teller > 0:
        print(f"[{label}] Ruis genegeerd: {ruis_teller} vlekje(s), "
              f"grootste={ruis_max:.0f} px  (drempel={p.min_area} px)")

    return resultaten


def verwijder_dubbelen(rijpe, onrijpe, overlap_drempel=0.4):
    gefilterd = []
    for u in onrijpe:
        dubbel = False
        for r in rijpe:
            ix1 = max(u["x"], r["x"]);  iy1 = max(u["y"], r["y"])
            ix2 = min(u["x"] + u["w"], r["x"] + r["w"])
            iy2 = min(u["y"] + u["h"], r["y"] + r["h"])
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            intersect = (ix2 - ix1) * (iy2 - iy1)
            iou = intersect / (u["w"] * u["h"] + r["w"] * r["h"] - intersect)
            if iou >= overlap_drempel:
                dubbel = True
                break
        if not dubbel:
            gefilterd.append(u)
    return gefilterd


def teken_detecties(frame, detecties, richtingen):
    for d in detecties:
        kleur = COLOR_RIPE if d["rijp"] else COLOR_UNRIPE
        staat = "Rijp" if d["rijp"] else "Onrijp"
        cx, cy, x, y = d["cx"], d["cy"], d["x"], d["y"]
        cv2.circle(frame, (cx, cy), d["radius"], kleur, 2)
        cv2.rectangle(frame, (x, y), (x + d["w"], y + d["h"]), kleur, 2)
        cv2.putText(frame, f"{staat} ({d['kleur_ratio']:.0%})",
                    (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)

        if d["rijp"]:
            cv2.putText(frame, f"Z={d['z_mm']:.0f}mm ({d['z_methode']})",
                        (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, kleur, 1)

        sleutel  = maak_positie_sleutel(d)
        richting = richtingen.get(sleutel)
        if richting:
            cv2.putText(frame, richting,
                        (x, y + d["h"] + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, kleur, 2)


# ============================================================
# === BEWEGINGSRICHTING ======================================
# ============================================================

def bereken_rotatie(middelpunt, vorige_pos, huidige_pos):
    mx, my = middelpunt
    dx_oud = vorige_pos[0] - mx
    dy_oud = vorige_pos[1] - my
    dx_nw  = huidige_pos[0] - mx
    dy_nw  = huidige_pos[1] - my

    if math.hypot(dx_nw, dy_nw) < MIN_RADIUS_SCHIJF:
        return None

    hoek_oud = math.atan2(dy_oud, dx_oud)
    hoek_nw  = math.atan2(dy_nw,  dx_nw)
    delta    = math.degrees(hoek_nw - hoek_oud)
    delta    = (delta + 180) % 360 - 180

    if abs(delta) < MIN_HOEK_DELTA:
        return "STILSTAAND"
    return "LINKSOM" if delta > 0 else "RECHTSOM"


# ============================================================
# === POSITIE-HULPFUNCTIES ===================================
# ============================================================

def maak_positie_sleutel(d):
    soort = "RIJP" if d["rijp"] else "ONRIJP"
    return (round(d["cx"] / POSITION_GRID), round(d["cy"] / POSITION_GRID), soort)


# ============================================================
# === SOCKET-HULPFUNCTIES ====================================
# ============================================================

def maak_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def stuur_positie(sock, bericht, adres):
    try:
        sock.sendto(bericht.encode(), adres)
        return True
    except OSError as e:
        print(f"Socket fout: {e}")
        return False


# ============================================================
# === OPSTARTEN-CHECK ========================================
# ============================================================

def controleer_ffmpeg():
    import shutil
    if not (os.path.isfile(FFMPEG_PATH) or shutil.which(FFMPEG_PATH)):
        raise FileNotFoundError(
            f"FFmpeg niet gevonden op: {FFMPEG_PATH}\n"
            f"Pas FFMPEG_PATH aan of stel de omgevingsvariabele FFMPEG_PATH in."
        )


# ============================================================
# === HOOFDPROGRAMMA =========================================
# ============================================================

if __name__ == "__main__":
    controleer_ffmpeg()

    sock    = maak_socket()
    streamer = FrameStreamer(PI2_IP, PI2_PORT, RTSPStream.OUT_W, RTSPStream.OUT_H, TARGET_FPS)
    streamer.start()

    verstuurde_posities: dict[tuple, str]   = {}
    vorige_posities:     dict[tuple, tuple] = {}

    print(f"Verbinding maken met reCamera op {RTSP_URL} ...")
    stream = RTSPStream(RTSP_URL)
    stream.start()

    timeout = time.time() + 30
    while not stream.is_ready():
        if time.time() > timeout:
            print("Timeout: kon geen frame ontvangen van de reCamera!")
            stream.stop()
            streamer.stop()
            sock.close()
            exit(1)
        time.sleep(0.1)

    print("Verbonden! Druk op Q om te stoppen.")
    print(f"Stream actief naar Pi 2 op {PI2_IP}:{PI2_PORT}")

    laatste_frame_id = None

    try:
        while True:
            frame_id, frame = stream.read(last_seen_id=laatste_frame_id, timeout=0.1)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            if frame is None or frame_id == laatste_frame_id:
                continue
            laatste_frame_id = frame_id

            # --- Kleurverwerking ---
            blurred = cv2.GaussianBlur(frame, (3, 3), 0)
            hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            masker_rood   = pas_morfologie_toe(maak_rood_masker(hsv),   agressief=False)
            masker_onrijp = pas_morfologie_toe(maak_onrijp_masker(hsv), agressief=True)

            # --- Detectie ---
            rijpe_detecties   = detecteer_aardbeien(masker_rood,   rijp=True)
            onrijpe_detecties = detecteer_aardbeien(masker_onrijp, rijp=False)
            onrijpe_detecties = verwijder_dubbelen(rijpe_detecties, onrijpe_detecties)

            alle_detecties = rijpe_detecties + onrijpe_detecties

            # --- Bewegingsrichting berekenen ---
            richtingen:               dict[tuple, str]   = {}
            nieuwe_posities_beweging: dict[tuple, tuple] = {}

            for d in alle_detecties:
                sleutel     = maak_positie_sleutel(d)
                huidige_pos = (d["cx"], d["cy"])

                if sleutel in vorige_posities:
                    richting = bereken_rotatie(
                        SCHIJF_MIDDELPUNT,
                        vorige_posities[sleutel],
                        huidige_pos,
                    )
                    if richting:
                        richtingen[sleutel] = richting

                nieuwe_posities_beweging[sleutel] = huidige_pos

            vorige_posities = nieuwe_posities_beweging

            # --- Tekenen ---
            teken_detecties(frame, alle_detecties, richtingen)

            if DEBUG_SCHIJF:
                mx, my = SCHIJF_MIDDELPUNT
                cv2.drawMarker(frame, (mx, my), (0, 0, 255),
                               cv2.MARKER_CROSS, 30, 2)
                cv2.putText(frame, "Middelpunt", (mx + 10, my - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            # --- Posities versturen via UDP naar ROS ---
            nieuwe_posities: dict[tuple, str] = {}

            for d in rijpe_detecties:
                sleutel  = maak_positie_sleutel(d)
                richting = richtingen.get(sleutel, "ONBEKEND")
                nieuwe_posities[sleutel] = (
                    f"RIJP,{d['cx']},{d['cy']},{d['z_mm']:.0f},{richting}"
                )

            for d in onrijpe_detecties:
                sleutel  = maak_positie_sleutel(d)
                richting = richtingen.get(sleutel, "ONBEKEND")
                nieuwe_posities[sleutel] = (
                    f"ONRIJP,{d['cx']},{d['cy']},{d['z_mm']:.0f},{richting}"
                )

            for sleutel, bericht in nieuwe_posities.items():
                if verstuurde_posities.get(sleutel) != bericht:
                    if stuur_positie(sock, bericht, (ROS_IP, ROS_PORT)):
                        verstuurde_posities[sleutel] = bericht

            for sleutel in list(verstuurde_posities):
                if sleutel not in nieuwe_posities:
                    del verstuurde_posities[sleutel]

            # --- Legenda ---
            cv2.putText(frame, "Groen kader = Rijp",    (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_RIPE,   2)
            cv2.putText(frame, "Oranje kader = Onrijp", (10, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_UNRIPE, 2)

            # --- Verwerkt frame naar Pi 2 sturen ---
            streamer.stuur_frame(frame)

            cv2.imshow("reCamera - Aardbeidetectie", frame)
            cv2.imshow("Rood Masker",   masker_rood)
            cv2.imshow("Onrijp Masker", masker_onrijp)

    finally:
        streamer.stop()
        stream.stop()
        sock.close()
        cv2.destroyAllWindows()