import numpy as np
import cv2
import threading
import time
import socket

# === STEL HIER HET IP-ADRES VAN JE reCamera IN ===
RECAMERA_IP = "192.168.42.1"
RTSP_URL = f"rtsp://admin:admin@{RECAMERA_IP}:554/live"

# === SOCKET INSTELLINGEN ===
ROS_IP = "127.0.0.1"
ROS_PORT = 5005

# === DETECTIE-PARAMETERS (pas hier aan i.p.v. in de code) ===
MIN_AREA = 6000          # Minimale contouroppervlakte in pixels
MAX_AREA = 120000        # Maximale contouroppervlakte in pixels
MIN_ASPECT_RATIO = 0.4   # Minimale breedte/hoogte verhouding
MAX_ASPECT_RATIO = 1.6   # Maximale breedte/hoogte verhouding
MIN_CIRCULARITY = 0.25   # Minimale cirkelvormigheid (0–1)
MIN_HU_0 = 0.01          # Ondergrens Hu-moment [0] voor aardbeivorm
MAX_HU_0 = 0.35          # Bovengrens Hu-moment [0] voor aardbeivorm
MIN_RED_RATIO = 0.5      # Minimale fractie rode pixels binnen contour

# Debug-modus: zet op False om afwijzingsberichten te onderdrukken
DEBUG = False

# Reconnect instellingen
MAX_RECONNECT_ATTEMPTS = 10   # Maximaal aantal herverbindingspogingen (None = oneindig)
RECONNECT_BACKOFF = 2.0       # Wachttijd in seconden tussen pogingen

# HSV-grenzen voor aardbei-rood
lower_red1 = np.array([0, 120, 80])
upper_red1 = np.array([10, 255, 220])
lower_red2 = np.array([170, 120, 80])
upper_red2 = np.array([180, 255, 220])

# Morphologie-kernels (eenmalig aanmaken, buiten de loop)
KERNEL_SMALL = np.ones((3, 3), np.uint8)
KERNEL_MEDIUM = np.ones((7, 7), np.uint8)


class RTSPStream:
    """Leest RTSP-frames in een aparte thread zodat de buffer niet volloopt."""

    def __init__(self, url):
        self.url = url
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.cap = None
        self.reconnect_attempts = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def _connect(self):
        """
        Maakt (opnieuw) verbinding met de RTSP-stream.
        Mag NIET worden aangeroepen terwijl self.lock al vastzit.
        """
        if self.cap:
            self.cap.release()
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        with self.lock:
            self.cap = cap

    def _read_loop(self):
        self._connect()
        while self.running:
            # FIX 1: check én read in één lock-blok om race condition te voorkomen
            with self.lock:
                cap_ready = self.cap is not None and self.cap.isOpened()
                if cap_ready:
                    ret, frame = self.cap.read()

            if not cap_ready:
                self.reconnect_attempts += 1
                if MAX_RECONNECT_ATTEMPTS is not None and self.reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                    print(f"Maximaal aantal herverbindingspogingen ({MAX_RECONNECT_ATTEMPTS}) bereikt. Stoppen.")
                    self.running = False
                    break
                print(f"Herverbinden (poging {self.reconnect_attempts})...")
                time.sleep(RECONNECT_BACKOFF)
                self._connect()
                continue

            if ret and frame is not None:
                with self.lock:
                    self.frame = frame
                self.reconnect_attempts = 0  # Reset teller bij succesvolle read
            else:
                print("Frame mislukt, herverbinden...")
                time.sleep(1)
                self._connect()

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def is_ready(self):
        with self.lock:
            return self.frame is not None

    def stop(self):
        self.running = False
        with self.lock:
            if self.cap:
                self.cap.release()


def maak_socket():
    """Maakt een UDP-socket aan."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def stuur_positie(sock, positie, adres):
    """Stuurt een positiestring via UDP. Geeft True terug bij succes."""
    try:
        sock.sendto(positie.encode(), adres)
        return True
    except OSError as e:
        print(f"Socket fout: {e}")
        return False


def detecteer_aardbeien(frame, mask_red):
    """
    Zoekt aardbeien in het frame op basis van het rode masker.
    Geeft een lijst terug van (cx, cy, x, y, w, h, radius, red_ratio) per gevonden aardbei.
    """
    contours, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    resultaten = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_AREA or area > MAX_AREA:
            if DEBUG:
                print(f"Afgewezen op oppervlak: {area:.0f}")
            continue

        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h
        if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
            if DEBUG:
                print(f"Afgewezen op aspect ratio: {aspect_ratio:.2f}")
            continue

        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        if circularity < MIN_CIRCULARITY:
            if DEBUG:
                print(f"Afgewezen op circulariteit: {circularity:.2f}")
            continue

        # --- Hu-momentenfilter ---
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue
        hu = cv2.HuMoments(moments).flatten()
        if hu[0] < MIN_HU_0 or hu[0] > MAX_HU_0:
            continue

        # --- Rood-ratiofilter ---
        mask_roi = np.zeros(mask_red.shape, np.uint8)
        cv2.drawContours(mask_roi, [contour], -1, 255, -1)
        red_pixels = cv2.countNonZero(cv2.bitwise_and(mask_red, mask_red, mask=mask_roi))
        total_pixels = cv2.countNonZero(mask_roi)
        red_ratio = red_pixels / total_pixels if total_pixels > 0 else 0
        if red_ratio < MIN_RED_RATIO:
            continue

        # FIX 2: radius direct uit minEnclosingCircle gebruiken i.p.v. weggooien en opnieuw berekenen
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        resultaten.append((int(cx), int(cy), x, y, w, h, int(radius), red_ratio))

    return resultaten


def teken_detecties(frame, detecties):
    """Tekent bounding boxes en labels op het frame."""
    for cx, cy, x, y, w, h, radius, red_ratio in detecties:
        cv2.circle(frame, (cx, cy), radius, (0, 255, 0), 2)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(frame, f"Aardbei! ({red_ratio:.0%} rood)", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


# ============================================================
# === HOOFDPROGRAMMA =========================================
# ============================================================

sock = maak_socket()

# FIX 3: verstuurde posities bijhouden als set, zodat bij meerdere aardbeien
#         elke positie correct vergeleken wordt met de laatste verstuurde waarde.
verstuurde_posities = {}  # {index: laatste_positie_string}

print(f"Verbinding maken met reCamera op {RTSP_URL} ...")
stream = RTSPStream(RTSP_URL)
stream.start()

# Wacht tot eerste frame beschikbaar is (max 10 sec)
timeout = time.time() + 10
while not stream.is_ready():
    if time.time() > timeout:
        print("Timeout: kon geen frame ontvangen van de reCamera!")
        stream.stop()
        sock.close()
        exit()
    time.sleep(0.1)

print("Verbonden! Druk op Q om te stoppen.")

while True:
    frame = stream.read()

    if frame is None:
        time.sleep(0.01)
        continue

    frame = cv2.resize(frame, (854, 480))

    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)

    # FIX 4: kernels worden gebruikt die eenmalig bovenaan zijn aangemaakt
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, KERNEL_SMALL)
    mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_DILATE, KERNEL_MEDIUM)

    detecties = detecteer_aardbeien(frame, mask_red)
    teken_detecties(frame, detecties)

    # === Stuur posities naar ROS2 ===
    # FIX 3 (vervolg): elke aardbei krijgt een eigen index als sleutel,
    #                  zodat posities per aardbei correct worden vergeleken.
    nieuwe_posities = {}
    for i, (cx, cy, *_) in enumerate(detecties):
        huidige_positie = f"{cx},{cy}"
        nieuwe_posities[i] = huidige_positie
        if verstuurde_posities.get(i) != huidige_positie:
            if stuur_positie(sock, huidige_positie, (ROS_IP, ROS_PORT)):
                verstuurde_posities[i] = huidige_positie
    # Verwijder posities van aardbeien die niet meer zichtbaar zijn
    verstuurde_posities.clear()
    verstuurde_posities.update(nieuwe_posities)

    cv2.imshow('reCamera - Aardbeidetectie', frame)
    cv2.imshow('Rood Masker', mask_red)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

stream.stop()
sock.close()
cv2.destroyAllWindows()