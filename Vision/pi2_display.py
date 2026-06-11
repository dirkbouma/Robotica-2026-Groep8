import cv2
import subprocess
import numpy as np

PI2_PORT    = 5000
W, H        = 854, 480
FRAME_BYTES = W * H * 3

cmd = [
    "ffmpeg",
    "-loglevel",  "error",
    "-fflags",    "nobuffer",
    "-flags",     "low_delay",
    "-i",         f"udp://0.0.0.0:{PI2_PORT}?overrun_nonfatal=1&fifo_size=50000000",
    "-f",         "rawvideo",
    "-pix_fmt",   "bgr24",
    "pipe:1",
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
buf  = bytearray(FRAME_BYTES)
mv   = memoryview(buf)

print(f"Wachten op stream van Pi 1 op poort {PI2_PORT}...")

while True:
    bytes_gelezen = 0
    while bytes_gelezen < FRAME_BYTES:
        n = proc.stdout.readinto(mv[bytes_gelezen:])
        if not n:
            break
        bytes_gelezen += n

    if bytes_gelezen != FRAME_BYTES:
        print("Stream onderbroken, wachten...")
        continue

    frame = np.frombuffer(buf, dtype=np.uint8).reshape((H, W, 3))
    cv2.imshow("reCamera - Display", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

proc.terminate()
cv2.destroyAllWindows()