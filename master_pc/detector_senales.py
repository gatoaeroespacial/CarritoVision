"""
detector_senales.py - Clase DetectorSenales.

Detecta octagonos ROJO (PARE) y VERDE (SIGA) sin aprendizaje profundo:
  1. Suavizado + conversion a HSV.
  2. Segmentacion por color con inRange (el rojo usa dos rangos porque el
     tono "envuelve" el 0/180 en HSV).
  3. Morfologia para limpiar la mascara.
  4. Contornos + aproximacion poligonal (approxPolyDP).
  5. Un contorno se acepta como octagono si: 7-10 vertices, es convexo
     (solidez alta), casi cuadrado en su caja, con circularidad alta y
     con relleno del circulo envolvente entre 0.72 y 0.93 (descarta circulos).
"""
from dataclasses import dataclass
from typing import Dict, Optional

import cv2
import numpy as np


@dataclass
class Senal:
    color: str                  # "rojo" o "verde"
    area_rel: float             # area / area del fotograma
    bbox: tuple                 # (x, y, w, h)
    vertices: int
    contorno: np.ndarray


class DetectorSenales:
    def __init__(self, cfg):
        self.cfg = cfg
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def _mascara(self, hsv, rangos):
        total = None
        for bajo, alto in rangos:
            m = cv2.inRange(hsv, np.array(bajo, np.uint8), np.array(alto, np.uint8))
            total = m if total is None else cv2.bitwise_or(total, m)
        total = cv2.morphologyEx(total, cv2.MORPH_OPEN, self._kernel)
        total = cv2.morphologyEx(total, cv2.MORPH_CLOSE, self._kernel)
        return total

    @staticmethod
    def _es_octagono(contorno):
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        if area <= 0 or perimetro <= 0:
            return False, 0
        vertices = len(cv2.approxPolyDP(contorno, 0.02 * perimetro, True))
        area_casco = cv2.contourArea(cv2.convexHull(contorno))
        solidez = area / area_casco if area_casco > 0 else 0
        _, _, w, h = cv2.boundingRect(contorno)
        relacion = w / float(h) if h else 0
        circularidad = 4 * np.pi * area / (perimetro ** 2)
        # Un octagono regular ocupa ~0.90 de su circulo envolvente minimo;
        # un circulo ~1.0 y un cuadrado ~0.64 (asi se distingue del circulo,
        # que tambien se aproxima con ~8 vertices).
        (_, _), radio = cv2.minEnclosingCircle(contorno)
        relleno = area / (np.pi * radio * radio) if radio > 0 else 0
        ok = (7 <= vertices <= 10 and solidez >= 0.90
              and 0.70 <= relacion <= 1.40 and circularidad >= 0.80
              and 0.72 <= relleno <= 0.93)
        return ok, vertices

    def _mejor(self, mascara, color, area_frame) -> Optional[Senal]:
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mejor = None
        for c in contornos:
            area_rel = cv2.contourArea(c) / float(area_frame)
            if area_rel < self.cfg.area_min_deteccion:
                continue
            ok, vertices = self._es_octagono(c)
            if not ok:
                continue
            if mejor is None or area_rel > mejor.area_rel:
                mejor = Senal(color, area_rel, cv2.boundingRect(c), vertices, c)
        return mejor

    def detectar(self, frame) -> Dict[str, Optional[Senal]]:
        alto, ancho = frame.shape[:2]
        hsv = cv2.cvtColor(cv2.GaussianBlur(frame, (5, 5), 0), cv2.COLOR_BGR2HSV)
        area_frame = alto * ancho
        rojo = self._mascara(hsv, (self.cfg.rojo_a, self.cfg.rojo_b))
        verde = self._mascara(hsv, (self.cfg.verde,))
        return {"rojo": self._mejor(rojo, "rojo", area_frame),
                "verde": self._mejor(verde, "verde", area_frame)}
