#!/usr/bin/env python3
"""
ROS2 Node: Kleurdetectie via reCamera RTSP-stream
==================================================
Detecteert rood, groen en wit in het camerabeeld van de grijper.

Publiceert:
  /kleur/frame          → sensor_msgs/Image  (geannoteerd frame)
  /kleur/masker_rood    → sensor_msgs/Image
  /kleur/masker_groen   → sensor_msgs/Image
  /kleur/masker_wit     → sensor_msgs/Image
  /kleur/detecties      → std_msgs/String    (JSON-array met gevonden objecten)

Diensten:
  /kleur/set_debug      → std_srvs/SetBool

Parameters:
  recamera_ip        (string, default "192.168.42.1")
  recamera_user      (string, default "admin")
  recamera_pass      (string, default "admin")
  ffmpeg_path        (string, default "ffmpeg")
  target_fps         (int,    default 30)
  min_area           (int,    default 500)   ← minimale contourgrootte in pixels
  stream_naar_pi2    (bool,   default False)
  pi2_ip             (string, default "192.168.1.100")
  pi2_port           (int,    default 5000)
  debug              (bool,   default False)

Gebruik:
  ros2 run aardbeien_detectie kleur_node
  ros2 run aardbeien_detectie kleur_node --ros-args \
      -p recamera_ip:=192.168.42.1 -p stream_naar_pi2:=true -p pi2_ip:=192.168.1.50
"""

import json
import subprocess
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from std_srvs.srv import SetBool


# ============================================================
# === HSV-DREMPELS ===========================================
# ============================================================

LOWER_RED1  = np.array([0,   100, 100])
UPPER_RED1  = np.array([10,  255, 255])
LOWER_RED2  = np.array([170, 100, 100])
UPPER_RED2  = np.array([180, 255, 255])

LOWER_GREEN = np.array([35,  50,  50])
UPPER_GREEN = np.array([85,  255, 255])

LOWER_WHITE = np.array([0,   0,   180])
UPPER_WHITE = np.array([180, 50,  255])

KERNEL = np.ones((5, 5), np.uint8)

# Visualisatiekleuren (BGR)
COLOR_ROOD  = (0,   0,   255)
COLOR_GROEN = (0,   255, 0)
COLOR_WIT   = (255, 255, 255)


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

def maak_maskers(hsv: np.ndarray):
    mask_rood = cv2.bitwise_or(
        cv2.inRange(hsv, LOWER_RED1, UPPER_RED1),
        cv2.inRange(hsv, LOWER_RED2, UPPER_RED2),
    )
    mask_groen = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
    mask_wit   = cv2.inRange(hsv, LOWER_WHITE, UPPER_WHITE)

    mask_rood  = cv2.morphologyEx(mask_rood,  cv2.MORPH_OPEN, KERNEL)
    mask_groen = cv2.morphologyEx(mask_groen, cv2.MORPH_OPEN, KERNEL)
    mask_wit   = cv2.morphologyEx(mask_wit,   cv2.MORPH_OPEN, KERNEL)

    return mask_rood, mask_groen, mask_wit


@dataclass
class KleurDetectie:
    kleur: str
    x: int
    y: int
    w: int
    h: int
    cx: int
    cy: int
    area: float


def detecteer_kleur(masker: np.ndarray, naam: str,
                    min_area: int, debug: bool) -> list[KleurDetectie]:
    contours, _ = cv2.findContours(
        masker, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    resultaten = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w // 2
        cy = y + h // 2
        if debug:
            print(f"[{naam}] ✓ area={area:.0f}, bbox={w}x{h}, center=({cx},{cy})")
        resultaten.append(KleurDetectie(
            kleur=naam, x=x, y=y, w=w, h=h, cx=cx, cy=cy, area=area
        ))
    return resultaten


def teken_detecties(frame: np.ndarray, detecties: list[KleurDetectie],
                    kleur_map: dict):
    for d in detecties:
        kleur = kleur_map[d.kleur]
        cv2.rectangle(frame, (d.x, d.y), (d.x + d.w, d.y + d.h), kleur, 2)
        cv2.putText(frame, d.kleur, (d.x, d.y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, kleur, 2)
        cv2.circle(frame, (d.cx, d.cy), 4, kleur, -1)


# ============================================================
# === ROS2 NODE ==============================================
# ============================================================

class KleurDetectieNode(Node):
    """
    Detecteert rood, groen en wit in het camerabeeld van de grijper
    en publiceert de resultaten als ROS2-topics.
    """

    KLEUR_MAP = {
        "ROOD":  COLOR_ROOD,
        "GROEN": COLOR_GROEN,
        "WIT":   COLOR_WIT,
    }

    def __init__(self):
        super().__init__("kleur_detectie")

        # ---- Parameters ----
        self.declare_parameter("recamera_ip",     "192.168.42.1")
        self.declare_parameter("recamera_user",   "admin")
        self.declare_parameter("recamera_pass",   "admin")
        self.declare_parameter("ffmpeg_path",     "ffmpeg")
        self.declare_parameter("target_fps",      30)
        self.declare_parameter("min_area",        500)
        self.declare_parameter("stream_naar_pi2", False)
        self.declare_parameter("pi2_ip",          "192.168.1.100")
        self.declare_parameter("pi2_port",        5000)
        self.declare_parameter("debug",           False)

        self._lees_params()
        self.add_on_set_parameters_callback(self._on_param_change)

        # ---- State ----
        self._bridge    = CvBridge()
        self._stream:   RTSPStream    | None = None
        self._streamer: FrameStreamer | None = None
        self._stop_event = threading.Event()

        # ---- QoS ----
        qos_img = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        qos_rel = QoSProfile(depth=10)

        # ---- Publishers ----
        self._pub_frame         = self.create_publisher(Image,  "kleur/frame",         qos_img)
        self._pub_masker_rood   = self.create_publisher(Image,  "kleur/masker_rood",   qos_img)
        self._pub_masker_groen  = self.create_publisher(Image,  "kleur/masker_groen",  qos_img)
        self._pub_masker_wit    = self.create_publisher(Image,  "kleur/masker_wit",    qos_img)
        self._pub_detecties     = self.create_publisher(String, "kleur/detecties",     qos_rel)

        # ---- Service ----
        self.create_service(SetBool, "kleur/set_debug", self._cb_set_debug)

        # ---- Starten ----
        self._start_alles()

        self.get_logger().info(
            f"KleurDetectieNode gestart — RTSP: {self._rtsp_url}"
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
        self._min_area    = self.get_parameter("min_area").value
        self._stream_pi2  = self.get_parameter("stream_naar_pi2").value
        self._pi2_ip      = self.get_parameter("pi2_ip").value
        self._pi2_port    = self.get_parameter("pi2_port").value
        self._debug       = self.get_parameter("debug").value

    def _on_param_change(self, params):
        herstart = False
        for p in params:
            if p.name in ("recamera_ip", "recamera_user", "recamera_pass",
                          "ffmpeg_path", "target_fps", "stream_naar_pi2",
                          "pi2_ip", "pi2_port"):
                herstart = True
            elif p.name == "min_area":
                self._min_area = p.value
            elif p.name == "debug":
                self._debug = p.value
                self.get_logger().info(f"Debug: {self._debug}")

        if herstart:
            self._lees_params()
            self._start_alles()

        return SetParametersResult(successful=True)

    # ----------------------------------------------------------
    # Opstarten
    # ----------------------------------------------------------

    def _start_alles(self):
        self._stop_event.set()
        if hasattr(self, "_verwerkings_thread") and self._verwerkings_thread.is_alive():
            self._verwerkings_thread.join(timeout=3)
        self._stop_event.clear()

        if self._stream:
            self._stream.stop()
        if self._streamer:
            self._streamer.stop()
            self._streamer = None

        self._stream = RTSPStream(
            url=self._rtsp_url,
            fps=self._target_fps,
            ffmpeg_path=self._ffmpeg_path,
        )
        self._stream.start()

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
            self.get_logger().info(
                f"Framestream actief → {self._pi2_ip}:{self._pi2_port}"
            )

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
    # Verwerkingsloop
    # ----------------------------------------------------------

    def _verwerkings_loop(self):
        laatste_frame_id = None

        while not self._stop_event.is_set():
            if not self._stream or not self._stream.is_ready():
                time.sleep(0.05)
                continue

            frame_id, frame = self._stream.read(
                last_seen_id=laatste_frame_id, timeout=0.1
            )

            if frame is None or frame_id == laatste_frame_id:
                continue
            laatste_frame_id = frame_id

            self._verwerk_frame(frame)

    def _verwerk_frame(self, frame: np.ndarray):
        # ---- Maskers ----
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask_rood, mask_groen, mask_wit = maak_maskers(hsv)

        # ---- Detectie ----
        detecties = (
            detecteer_kleur(mask_rood,  "ROOD",  self._min_area, self._debug)
            + detecteer_kleur(mask_groen, "GROEN", self._min_area, self._debug)
            + detecteer_kleur(mask_wit,   "WIT",   self._min_area, self._debug)
        )

        # ---- Annotaties ----
        teken_detecties(frame, detecties, self.KLEUR_MAP)

        cv2.putText(frame, "Rood / Groen / Wit detectie", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # ---- Publiceer beelden ----
        self._pub_frame.publish(
            self._bridge.cv2_to_imgmsg(frame, encoding="bgr8"))
        self._pub_masker_rood.publish(
            self._bridge.cv2_to_imgmsg(mask_rood,  encoding="mono8"))
        self._pub_masker_groen.publish(
            self._bridge.cv2_to_imgmsg(mask_groen, encoding="mono8"))
        self._pub_masker_wit.publish(
            self._bridge.cv2_to_imgmsg(mask_wit,   encoding="mono8"))

        # ---- Publiceer JSON ----
        payload = [
            {
                "kleur": d.kleur,
                "cx":    d.cx,
                "cy":    d.cy,
                "x":     d.x,
                "y":     d.y,
                "w":     d.w,
                "h":     d.h,
                "area":  round(d.area, 1),
            }
            for d in detecties
        ]
        self._pub_detecties.publish(String(data=json.dumps(payload)))

        # ---- Stream naar Pi 2 ----
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
        super().destroy_node()


# ============================================================
# === ENTRY POINT ============================================
# ============================================================

def main(args=None):
    rclpy.init(args=args)
    node = KleurDetectieNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()