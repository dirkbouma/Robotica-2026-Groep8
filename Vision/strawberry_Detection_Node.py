#!/usr/bin/env python3
"""
ROS2 Node: Aardbeidetectie via reCamera RTSP-stream
=====================================================
Publiceert:
  /aardbeien/detecties      → std_msgs/String         (JSON-array)
  /aardbeien/rijp           → geometry_msgs/PoseArray (rijpe bessen)
  /aardbeien/onrijp         → geometry_msgs/PoseArray (onrijpe bessen)
  /aardbeien/frame          → sensor_msgs/Image        (geannoteerd frame)
  /aardbeien/masker_rood    → sensor_msgs/Image
  /aardbeien/masker_onrijp  → sensor_msgs/Image

Diensten:
  /aardbeien/set_debug      → std_srvs/SetBool

Parameters (declareerbaar via ros2 param / YAML):
  recamera_ip        (string,  default "192.168.42.1")
  recamera_user      (string,  default "admin")
  recamera_pass      (string,  default "admin")
  ffmpeg_path        (string,  default "ffmpeg")
  target_fps         (int,     default 30)
  stream_naar_pi2    (bool,    default False)
  pi2_ip             (string,  default "192.168.1.100")
  pi2_port           (int,     default 5000)
  legacy_udp         (bool,    default False)
  debug              (bool,    default False)
  debug_schijf       (bool,    default False)

Gebruik:
  ros2 run aardbeien_detectie detectie_node
  ros2 run aardbeien_detectie detectie_node --ros-args \
      -p recamera_ip:=192.168.42.1 -p stream_naar_pi2:=true -p pi2_ip:=192.168.1.50
"""

import json
import math
import socket
import subprocess
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Pose, PoseArray
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from std_srvs.srv import SetBool


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
    min_area=500,   max_area=50000,
    min_aspect=0.2, max_aspect=1.8,
    min_circularity=0.35, min_solidity=0.65, min_color_ratio=0.65,
)

ONRIJP_PARAMS = DetectieParams(
    min_area=1200,  max_area=15000,
    min_aspect=0.42, max_aspect=1.6,
    min_circularity=0.25, min_solidity=0.60, min_color_ratio=0.55,
)

# ============================================================
# === DIEPTE-INSTELLINGEN ====================================
# ============================================================

ECHTE_DIAMETER_MM = 40
FOCAL_LENGTH_PX   = 600
TAFEL_Z_MM        = 350
MIN_RADIUS_DIEPTE = 8
DIEPTE_MAX_MM     = 1500

# ============================================================
# === BEWEGINGSINSTELLINGEN ==================================
# ============================================================

SCHIJF_MIDDELPUNT = (427, 240)
MIN_HOEK_DELTA    = 0.8
MIN_RADIUS_SCHIJF = 30
POSITION_GRID     = 40

# ============================================================
# === HSV-DREMPELS ===========================================
# ============================================================

lower_red1 = np.array([0,   150, 100])
upper_red1 = np.array([8,   255, 255])
lower_red2 = np.array([172, 150, 100])
upper_red2 = np.array([180, 255, 255])

lower_unripe_blauw = np.array([88,  35,  60])
upper_unripe_blauw = np.array([108, 110, 190])
lower_unripe_groen = np.array([55,  60,  25])
upper_unripe_groen = np.array([80,  200, 120])

KERNEL_SMALL  = np.ones((3, 3), np.uint8)
KERNEL_MEDIUM = np.ones((5, 5), np.uint8)

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

    def __init__(self, url: str, fps: int, ffmpeg_path: str,
                 max_reconnects: int = 10, backoff: float = 2.0):
        self.url             = url
        self.fps             = fps
        self.ffmpeg_path     = ffmpeg_path
        self.max_reconnects  = max_reconnects
        self.backoff         = backoff
        self.frame           = None
        self.frame_id        = 0
        self.lock            = threading.Lock()
        self._frame_event    = threading.Event()
        self.running         = False
        self._proc           = None
        self.reconnect_count = 0

    def start(self):
        self.running = True
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _spawn(self):
        self._kill()
        cmd = [
            self.ffmpeg_path,
            "-loglevel",        "error",
            "-rtsp_transport",  "tcp",
            "-fflags",          "nobuffer",
            "-flags",           "low_delay",
            "-analyzeduration", "1000000",
            "-probesize",       "1000000",
            "-i",               self.url,
            "-vf",              f"fps={self.fps},scale={self.OUT_W}:{self.OUT_H}",
            "-f",               "rawvideo",
            "-pix_fmt",         "bgr24",
            "pipe:1",
        ]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )

    def _kill(self):
        if self._proc:
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
                self.reconnect_count += 1
                if self.reconnect_count > self.max_reconnects:
                    break
                time.sleep(self.backoff)
                self._spawn()
                continue

            bytes_read = 0
            try:
                while bytes_read < self.FRAME_BYTES:
                    n = proc.stdout.readinto(mv[bytes_read:])
                    if not n:
                        break
                    bytes_read += n
            except Exception:
                bytes_read = 0

            if bytes_read != self.FRAME_BYTES:
                if self._proc and self._proc.poll() is not None:
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
            self.reconnect_count = 0

    def read(self, last_seen_id=None, timeout=0.1):
        """Blokkeert maximaal `timeout` seconden tot een nieuw frame beschikbaar is."""
        if last_seen_id is not None:
            with self.lock:
                current = self.frame_id
            if current == last_seen_id:
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
# === FRAME-STREAMER NAAR PI 2 ===============================
# ============================================================

class FrameStreamer:
    """
    Stuurt geannoteerde frames via FFmpeg als UDP/mpegts naar Pi 2 (display).
    Pi 2 ontvangt deze met de display_node (pi2_display_node.py).
    """

    def __init__(self, ip: str, port: int, w: int, h: int,
                 fps: int, ffmpeg_path: str):
        self.ip          = ip
        self.port        = port
        self.w           = w
        self.h           = h
        self.fps         = fps
        self.ffmpeg_path = ffmpeg_path
        self._proc       = None
        self._lock       = threading.Lock()

    def start(self):
        cmd = [
            self.ffmpeg_path,
            "-loglevel", "error",
            "-f",        "rawvideo",
            "-pix_fmt",  "bgr24",
            "-s",        f"{self.w}x{self.h}",
            "-r",        str(self.fps),
            "-i",        "pipe:0",
            "-c:v",      "libx264",
            "-preset",   "ultrafast",
            "-tune",     "zerolatency",
            "-f",        "mpegts",
            f"udp://{self.ip}:{self.port}?pkt_size=1316",
        ]
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0
        )

    def stuur_frame(self, frame: np.ndarray):
        if self._proc is None or self._proc.poll() is not None:
            self.start()
        try:
            with self._lock:
                self._proc.stdin.write(frame.tobytes())
        except Exception:
            pass

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
# === DETECTIE-HULPFUNCTIES ==================================
# ============================================================

def maak_rood_masker(hsv):
    m1 = cv2.inRange(hsv, lower_red1, upper_red1)
    m2 = cv2.inRange(hsv, lower_red2, upper_red2)
    return cv2.bitwise_or(m1, m2)


def maak_onrijp_masker(hsv):
    masker_blauw = cv2.inRange(hsv, lower_unripe_blauw, upper_unripe_blauw)
    masker_groen = cv2.inRange(hsv, lower_unripe_groen, upper_unripe_groen)
    blauw_groot  = cv2.dilate(masker_blauw, np.ones((30, 30), np.uint8))
    masker_groen = cv2.bitwise_and(masker_groen, blauw_groot)
    return cv2.bitwise_or(masker_blauw, masker_groen)


def pas_morfologie_toe(masker, agressief=False):
    masker = cv2.morphologyEx(masker, cv2.MORPH_OPEN,  KERNEL_SMALL)
    masker = cv2.morphologyEx(masker, cv2.MORPH_CLOSE, KERNEL_MEDIUM)
    if agressief:
        masker = cv2.morphologyEx(masker, cv2.MORPH_ERODE,  KERNEL_SMALL)
        masker = cv2.morphologyEx(masker, cv2.MORPH_DILATE, KERNEL_MEDIUM)
    return masker


def schat_diepte_mm(radius_px: int):
    if radius_px >= MIN_RADIUS_DIEPTE:
        z = (ECHTE_DIAMETER_MM * FOCAL_LENGTH_PX) / (2 * radius_px)
        if z <= DIEPTE_MAX_MM:
            return round(z, 1), "grootte"
    return float(TAFEL_Z_MM), "tafel"


def _kleur_ratio(masker, contour):
    x, y, w, h = cv2.boundingRect(contour)
    roi_masker  = masker[y:y + h, x:x + w]
    roi_cnt     = np.zeros((h, w), np.uint8)
    cv2.drawContours(roi_cnt, [contour - np.array([x, y])], -1, 255, cv2.FILLED)
    kleur  = cv2.countNonZero(cv2.bitwise_and(roi_masker, roi_cnt))
    totaal = cv2.countNonZero(roi_cnt)
    return kleur / totaal if totaal > 0 else 0.0


def detecteer_aardbeien(masker, rijp: bool, debug: bool = False):
    p     = RIJP_PARAMS if rijp else ONRIJP_PARAMS
    label = "RIJP"      if rijp else "ONRIJP"
    contours, _ = cv2.findContours(masker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    resultaten  = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if not (p.min_area <= area <= p.max_area):
            continue

        x, y, w, h = cv2.boundingRect(contour)
        ar = w / h
        if not (p.min_aspect <= ar <= p.max_aspect):
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / perimeter ** 2
        if circularity < p.min_circularity:
            continue

        hull_area = cv2.contourArea(cv2.convexHull(contour))
        solidity  = area / hull_area if hull_area > 0 else 0
        if solidity < p.min_solidity:
            continue

        kleur_ratio = _kleur_ratio(masker, contour)
        if kleur_ratio < p.min_color_ratio:
            continue

        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        r_int = int(radius)
        z_mm, z_methode = (
            schat_diepte_mm(r_int) if rijp else (float(TAFEL_Z_MM), "tafel")
        )

        if debug:
            print(f"[{label}] ✓ area={area:.0f}, AR={ar:.2f}, "
                  f"circ={circularity:.2f}, solid={solidity:.2f}, "
                  f"kleur={kleur_ratio:.0%}, Z={z_mm}mm")

        resultaten.append({
            "cx": int(cx), "cy": int(cy),
            "x": x, "y": y, "w": w, "h": h,
            "radius": r_int,
            "kleur_ratio": kleur_ratio,
            "rijp": rijp,
            "z_mm": z_mm,
            "z_methode": z_methode,
        })

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


def bereken_rotatie(middelpunt, vorige_pos, huidige_pos):
    mx, my  = middelpunt
    dx_oud  = vorige_pos[0] - mx
    dy_oud  = vorige_pos[1] - my
    dx_nw   = huidige_pos[0] - mx
    dy_nw   = huidige_pos[1] - my
    if math.hypot(dx_nw, dy_nw) < MIN_RADIUS_SCHIJF:
        return None
    hoek_oud = math.atan2(dy_oud, dx_oud)
    hoek_nw  = math.atan2(dy_nw,  dx_nw)
    delta    = math.degrees(hoek_nw - hoek_oud)
    delta    = (delta + 180) % 360 - 180
    if abs(delta) < MIN_HOEK_DELTA:
        return "STILSTAAND"
    return "LINKSOM" if delta > 0 else "RECHTSOM"


def maak_positie_sleutel(d):
    soort = "RIJP" if d["rijp"] else "ONRIJP"
    return (round(d["cx"] / POSITION_GRID), round(d["cy"] / POSITION_GRID), soort)


def teken_detecties(frame, detecties, richtingen):
    for d in detecties:
        kleur = COLOR_RIPE if d["rijp"] else COLOR_UNRIPE
        staat = "Rijp"    if d["rijp"] else "Onrijp"
        cx, cy, x, y = d["cx"], d["cy"], d["x"], d["y"]
        cv2.circle(frame, (cx, cy), d["radius"], kleur, 2)
        cv2.rectangle(frame, (x, y), (x + d["w"], y + d["h"]), kleur, 2)
        cv2.putText(frame, f"{staat} ({d['kleur_ratio']:.0%})",
                    (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)
        if d["rijp"]:
            cv2.putText(frame, f"Z={d['z_mm']:.0f}mm ({d['z_methode']})",
                        (x, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, kleur, 1)
        richting = richtingen.get(maak_positie_sleutel(d))
        if richting:
            cv2.putText(frame, richting, (x, y + d["h"] + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, kleur, 2)


def detectie_naar_pose(d) -> Pose:
    """
    Zet een detectie-dict om naar een geometry_msgs/Pose.
      position.x  = cx  (pixels, horizontaal)
      position.y  = cy  (pixels, verticaal)
      position.z  = z_mm (geschatte afstand in mm)
      orientation = identity quaternion
    """
    pose = Pose()
    pose.position.x = float(d["cx"])
    pose.position.y = float(d["cy"])
    pose.position.z = float(d["z_mm"])
    pose.orientation.w = 1.0
    return pose


# ============================================================
# === ROS2 NODE — PI 1 (detectie + stream) ===================
# ============================================================

class AardbeiDetectieNode(Node):
    """
    Hoofdnode op Pi 1.
    - Leest RTSP-stream van de reCamera op de grijper.
    - Voert aardbeidetectie uit.
    - Publiceert ROS2-topics (detecties, maskers, geannoteerd frame).
    - Stuurt geannoteerd frame optioneel via UDP/mpegts naar Pi 2 (display).
    - Stuurt optioneel legacy UDP-berichten naar een ROS1-bridge op poort 5005.
    """

    def __init__(self):
        super().__init__("aardbeien_detectie")

        # ---- Parameters declareren ----
        self.declare_parameter("recamera_ip",     "192.168.42.1")
        self.declare_parameter("recamera_user",   "admin")
        self.declare_parameter("recamera_pass",   "admin")
        self.declare_parameter("ffmpeg_path",     "ffmpeg")
        self.declare_parameter("target_fps",      30)
        self.declare_parameter("stream_naar_pi2", False)
        self.declare_parameter("pi2_ip",          "192.168.1.100")
        self.declare_parameter("pi2_port",        5000)
        self.declare_parameter("legacy_udp",      False)   # UDP naar poort 5005
        self.declare_parameter("debug",           False)
        self.declare_parameter("debug_schijf",    False)

        self._lees_params()
        self.add_on_set_parameters_callback(self._on_param_change)

        # ---- State ----
        self._bridge               = CvBridge()
        self._vorige_posities:     dict = {}
        self._verstuurde_posities: dict = {}
        self._stream:  RTSPStream   | None = None
        self._streamer: FrameStreamer | None = None
        self._sock:    socket.socket | None = None
        self._verwerkings_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # ---- QoS ----
        qos_img = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        qos_rel = QoSProfile(depth=10)

        # ---- Publishers ----
        self._pub_detecties     = self.create_publisher(String,    "aardbeien/detecties",     qos_rel)
        self._pub_rijp          = self.create_publisher(PoseArray, "aardbeien/rijp",           qos_rel)
        self._pub_onrijp        = self.create_publisher(PoseArray, "aardbeien/onrijp",         qos_rel)
        self._pub_frame         = self.create_publisher(Image,     "aardbeien/frame",          qos_img)
        self._pub_masker_rood   = self.create_publisher(Image,     "aardbeien/masker_rood",    qos_img)
        self._pub_masker_onrijp = self.create_publisher(Image,     "aardbeien/masker_onrijp",  qos_img)

        # ---- Service ----
        self._srv_debug = self.create_service(
            SetBool, "aardbeien/set_debug", self._cb_set_debug)

        # ---- Stream + verwerkingsthread starten ----
        self._start_alles()

        self.get_logger().info(
            f"AardbeiDetectieNode gestart — RTSP: {self._rtsp_url}"
        )
        if self._stream_pi2:
            self.get_logger().info(
                f"Framestream actief → {self._pi2_ip}:{self._pi2_port}"
            )

    # ----------------------------------------------------------
    # Parameters
    # ----------------------------------------------------------

    def _lees_params(self):
        ip   = self.get_parameter("recamera_ip").value
        user = self.get_parameter("recamera_user").value
        pwd  = self.get_parameter("recamera_pass").value
        self._rtsp_url    = f"rtsp://{user}:{pwd}@{ip}:554/live"
        self._ffmpeg_path = self.get_parameter("ffmpeg_path").value
        self._target_fps  = self.get_parameter("target_fps").value
        self._stream_pi2  = self.get_parameter("stream_naar_pi2").value
        self._pi2_ip      = self.get_parameter("pi2_ip").value
        self._pi2_port    = self.get_parameter("pi2_port").value
        self._legacy_udp  = self.get_parameter("legacy_udp").value
        self._debug       = self.get_parameter("debug").value
        self._debug_schijf = self.get_parameter("debug_schijf").value

    def _on_param_change(self, params):
        herstart = False
        for p in params:
            if p.name in ("recamera_ip", "recamera_user", "recamera_pass",
                          "ffmpeg_path", "target_fps"):
                herstart = True          # stream moet opnieuw starten
            elif p.name == "stream_naar_pi2":
                self._stream_pi2 = p.value
                herstart = True
            elif p.name == "pi2_ip":
                self._pi2_ip = p.value
                herstart = True
            elif p.name == "pi2_port":
                self._pi2_port = p.value
                herstart = True
            elif p.name == "legacy_udp":
                self._legacy_udp = p.value
                self._initialiseer_udp_socket()
            elif p.name == "debug":
                self._debug = p.value
                self.get_logger().info(f"Debug: {self._debug}")
            elif p.name == "debug_schijf":
                self._debug_schijf = p.value

        if herstart:
            self._lees_params()
            self._start_alles()

        return SetParametersResult(successful=True)

    # ----------------------------------------------------------
    # Opstarten / herstart
    # ----------------------------------------------------------

    def _initialiseer_udp_socket(self):
        """Maakt UDP-socket aan of sluit hem, afhankelijk van legacy_udp param."""
        if self._legacy_udp:
            if self._sock is None:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.get_logger().info("Legacy UDP socket geopend (poort 5005)")
        else:
            if self._sock is not None:
                self._sock.close()
                self._sock = None

    def _start_alles(self):
        # Stop bestaande verwerkingsthread
        self._stop_event.set()
        if self._verwerkings_thread and self._verwerkings_thread.is_alive():
            self._verwerkings_thread.join(timeout=3)
        self._stop_event.clear()

        # Stop bestaande stream en streamer
        if self._stream:
            self._stream.stop()
        if self._streamer:
            self._streamer.stop()
            self._streamer = None

        # UDP socket beheren
        self._initialiseer_udp_socket()

        # Nieuwe RTSP stream
        self._stream = RTSPStream(
            url=self._rtsp_url,
            fps=self._target_fps,
            ffmpeg_path=self._ffmpeg_path,
        )
        self._stream.start()

        # Optionele framestreamer naar Pi 2
        if self._stream_pi2:
            self._streamer = FrameStreamer(
                ip=self._pi2_ip,
                port=self._pi2_port,
                w=RTSPStream.OUT_W,
                h=RTSPStream.OUT_H,
                fps=self._target_fps,
                ffmpeg_path=self._ffmpeg_path,
            )
            self._streamer.start()

        # Verwerkingsthread (blokkeert op nieuwe frames — geen timer-conflict)
        self._verwerkings_thread = threading.Thread(
            target=self._verwerkings_loop, daemon=True
        )
        self._verwerkings_thread.start()

    # ----------------------------------------------------------
    # Service
    # ----------------------------------------------------------

    def _cb_set_debug(self, req, resp):
        self._debug = req.data
        resp.success = True
        resp.message = f"Debug {'aan' if self._debug else 'uit'}"
        self.get_logger().info(resp.message)
        return resp

    # ----------------------------------------------------------
    # Verwerkingsloop (eigen thread — geen ROS-timer)
    # ----------------------------------------------------------

    def _verwerkings_loop(self):
        laatste_frame_id = None

        while not self._stop_event.is_set():
            if not self._stream or not self._stream.is_ready():
                time.sleep(0.05)
                continue

            # Blokkeer tot nieuw frame (max 100 ms) — geen timer-conflict
            frame_id, frame = self._stream.read(
                last_seen_id=laatste_frame_id, timeout=0.1
            )

            if frame is None or frame_id == laatste_frame_id:
                continue
            laatste_frame_id = frame_id

            self._verwerk_frame(frame)

    def _verwerk_frame(self, frame: np.ndarray):
        now = self.get_clock().now().to_msg()

        # ---- Kleurverwerking ----
        blurred       = cv2.GaussianBlur(frame, (3, 3), 0)
        hsv           = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        masker_rood   = pas_morfologie_toe(maak_rood_masker(hsv),   agressief=False)
        masker_onrijp = pas_morfologie_toe(maak_onrijp_masker(hsv), agressief=True)

        # ---- Detectie ----
        rijpe   = detecteer_aardbeien(masker_rood,   rijp=True,  debug=self._debug)
        onrijpe = detecteer_aardbeien(masker_onrijp, rijp=False, debug=self._debug)
        onrijpe = verwijder_dubbelen(rijpe, onrijpe)
        alle    = rijpe + onrijpe

        # ---- Bewegingsrichting ----
        richtingen:     dict = {}
        nieuwe_posities: dict = {}

        for d in alle:
            sleutel = maak_positie_sleutel(d)
            huidig  = (d["cx"], d["cy"])
            if sleutel in self._vorige_posities:
                r = bereken_rotatie(
                    SCHIJF_MIDDELPUNT,
                    self._vorige_posities[sleutel],
                    huidig,
                )
                if r:
                    richtingen[sleutel] = r
            nieuwe_posities[sleutel] = huidig

        self._vorige_posities = nieuwe_posities

        # ---- Annotaties ----
        teken_detecties(frame, alle, richtingen)

        if self._debug_schijf:
            mx, my = SCHIJF_MIDDELPUNT
            cv2.drawMarker(frame, (mx, my), (0, 0, 255), cv2.MARKER_CROSS, 30, 2)
            cv2.putText(frame, "Middelpunt", (mx + 10, my - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        cv2.putText(frame, "Groen = Rijp",    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_RIPE,   2)
        cv2.putText(frame, "Oranje = Onrijp", (10, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_UNRIPE, 2)

        # ---- Publiceer beelden ----
        self._pub_frame.publish(
            self._bridge.cv2_to_imgmsg(frame, encoding="bgr8"))
        self._pub_masker_rood.publish(
            self._bridge.cv2_to_imgmsg(masker_rood, encoding="mono8"))
        self._pub_masker_onrijp.publish(
            self._bridge.cv2_to_imgmsg(masker_onrijp, encoding="mono8"))

        # ---- Publiceer PoseArrays ----
        def maak_pose_array(detecties):
            pa = PoseArray()
            pa.header.stamp    = now
            pa.header.frame_id = "camera_frame"
            pa.poses = [detectie_naar_pose(d) for d in detecties]
            return pa

        self._pub_rijp.publish(maak_pose_array(rijpe))
        self._pub_onrijp.publish(maak_pose_array(onrijpe))

        # ---- Publiceer JSON ----
        payload = []
        for d in alle:
            sleutel  = maak_positie_sleutel(d)
            richting = richtingen.get(sleutel, "ONBEKEND")
            payload.append({
                "rijp":        d["rijp"],
                "cx":          d["cx"],
                "cy":          d["cy"],
                "z_mm":        d["z_mm"],
                "z_methode":   d["z_methode"],
                "richting":    richting,
                "radius":      d["radius"],
                "kleur_ratio": round(d["kleur_ratio"], 3),
            })
        self._pub_detecties.publish(String(data=json.dumps(payload)))

        # ---- Legacy UDP (optioneel) ----
        if self._legacy_udp and self._sock:
            nieuwe_udp: dict = {}
            for d in rijpe:
                sleutel  = maak_positie_sleutel(d)
                richting = richtingen.get(sleutel, "ONBEKEND")
                nieuwe_udp[sleutel] = (
                    f"RIJP,{d['cx']},{d['cy']},{d['z_mm']:.0f},{richting}"
                )
            for d in onrijpe:
                sleutel  = maak_positie_sleutel(d)
                richting = richtingen.get(sleutel, "ONBEKEND")
                nieuwe_udp[sleutel] = (
                    f"ONRIJP,{d['cx']},{d['cy']},{d['z_mm']:.0f},{richting}"
                )
            for sleutel, bericht in nieuwe_udp.items():
                if self._verstuurde_posities.get(sleutel) != bericht:
                    try:
                        self._sock.sendto(bericht.encode(), ("127.0.0.1", 5005))
                        self._verstuurde_posities[sleutel] = bericht
                    except OSError as e:
                        self.get_logger().warn(f"UDP fout: {e}")
            for sleutel in list(self._verstuurde_posities):
                if sleutel not in nieuwe_udp:
                    del self._verstuurde_posities[sleutel]

        # ---- Stream naar Pi 2 (display) ----
        if self._streamer:
            self._streamer.stuur_frame(frame)

    # ----------------------------------------------------------
    # Opruimen
    # ----------------------------------------------------------

    def destroy_node(self):
        self._stop_event.set()
        if self._stream:
            self._stream.stop()
        if self._streamer:
            self._streamer.stop()
        if self._sock:
            self._sock.close()
        super().destroy_node()


# ============================================================
# === ENTRY POINT — PI 1 =====================================
# ============================================================

def main(args=None):
    rclpy.init(args=args)
    node = AardbeiDetectieNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()