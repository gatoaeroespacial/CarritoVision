"""
Calibrador de color HSV. Sirve para hallar los rangos de ROJO y VERDE con la
luz real de la pista. Uso (desde master_pc):
    python herramientas/calibrar_hsv.py --fuente http://IP:8080/video
Mueve las barras hasta que SOLO el octagono quede blanco en la mascara.
Teclas: 's' imprime los valores para pegarlos en config.py | 'q' salir
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from camara import Camara  # noqa: E402


def nada(_):
    pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fuente", default="0")
    a = p.parse_args()
    cam = Camara(a.fuente, 640, 480)
    cam.iniciar()
    cv2.namedWindow("Ajustes")
    for nombre, ini, tope in (("H min", 0, 179), ("H max", 10, 179), ("S min", 120, 255),
                              ("S max", 255, 255), ("V min", 70, 255), ("V max", 255, 255)):
        cv2.createTrackbar(nombre, "Ajustes", ini, tope, nada)
    try:
        while True:
            ok, frame = cam.leer()
            if not ok:
                if cam.terminada:
                    break
                continue
            hsv = cv2.cvtColor(cv2.GaussianBlur(frame, (5, 5), 0), cv2.COLOR_BGR2HSV)
            v = [cv2.getTrackbarPos(n, "Ajustes") for n in
                 ("H min", "H max", "S min", "S max", "V min", "V max")]
            mask = cv2.inRange(hsv, np.array([v[0], v[2], v[4]]), np.array([v[1], v[3], v[5]]))
            cv2.imshow("Camara", frame)
            cv2.imshow("Mascara", mask)
            k = cv2.waitKey(1) & 0xFF
            if k == ord("s"):
                print(f"(({v[0]}, {v[2]}, {v[4]}), ({v[1]}, {v[3]}, {v[5]}))")
            if k == ord("q"):
                break
    finally:
        cam.liberar()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
