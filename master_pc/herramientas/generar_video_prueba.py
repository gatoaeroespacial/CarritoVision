"""
Genera un video sintetico (prueba.mp4) para probar SIN robot ni pista:
  linea negra curva, octagono ROJO (dos veces), octagono VERDE y un tramo
  donde la linea desaparece. Uso (desde master_pc):
      python herramientas/generar_video_prueba.py prueba.mp4
"""
import sys

import cv2
import numpy as np

W, H, FPS, N = 640, 480, 30, 600


def octagono(img, centro, r, color):
    cx, cy = centro
    pts = [(int(cx + r * np.cos(np.radians(22.5 + 45 * k))),
            int(cy + r * np.sin(np.radians(22.5 + 45 * k)))) for k in range(8)]
    cv2.fillPoly(img, [np.array(pts, np.int32)], color)
    if r > 30:
        cv2.putText(img, "STOP" if color[2] > 150 else "GO", (cx - int(r * 0.5), cy + int(r * 0.12)),
                    cv2.FONT_HERSHEY_SIMPLEX, r / 100.0, (255, 255, 255), 1)


def fotograma(t, rng):
    img = np.full((H, W, 3), 205, np.uint8)
    grad = np.linspace(-15, 15, W).astype(np.int16)[None, :, None]
    img = np.clip(img.astype(np.int16) + grad, 0, 255).astype(np.uint8)

    if not (500 <= t < 530):  # tramo sin linea
        pts = []
        for y in range(H, -1, -10):
            x = 320 + 110 * np.sin(2 * np.pi * t / 300 + y * 0.006)
            pts.append((int(x), y))
        cv2.polylines(img, [np.array(pts, np.int32)], False, (25, 25, 25), 34)

    for ini, fin in ((100, 220), (400, 470)):        # ROJO
        if ini <= t < fin:
            octagono(img, (520, 120 + int((t - ini) * 0.7)), 15 + int((t - ini) * 0.6), (30, 30, 200))
    if 300 <= t < 360:                                # VERDE
        octagono(img, (130, 120 + int((t - 300) * 0.7)), 15 + int((t - 300) * 0.9), (40, 170, 40))

    ruido = rng.normal(0, 4, img.shape)
    return np.clip(img + ruido, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    salida = sys.argv[1] if len(sys.argv) > 1 else "prueba.mp4"
    rng = np.random.default_rng(1)
    w = cv2.VideoWriter(salida, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for t in range(N):
        w.write(fotograma(t, rng))
    w.release()
    print(f"Video generado: {salida} ({N} fotogramas, {N / FPS:.0f} s)")
