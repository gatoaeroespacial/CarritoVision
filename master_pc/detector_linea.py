"""
detector_linea.py - Clase DetectorLinea.

Etapas (para explicar en el poster):
  1. ROI: se recorta la parte baja de la imagen (lo que esta justo delante del robot).
  2. Gris + suavizado gaussiano para reducir ruido.
  3. Umbralizacion (Otsu automatico o fija) para separar linea y piso.
  4. Se descartan pixeles muy coloridos (las senales rojo/verde no son la linea).
  5. Morfologia (apertura + cierre) para quitar puntos sueltos y cerrar huecos.
  6. Contornos: se toma el mas grande y se calcula su centroide (momentos).
  7. error = (cx - centro) / (ancho/2)  -> [-1, 1]. Negativo = linea a la izquierda.
"""
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class ResultadoLinea:
    visible: bool
    cx: Optional[int] = None
    cy: Optional[int] = None
    error: Optional[float] = None
    area_rel: float = 0.0
    y0: int = 0
    mascara: Optional[np.ndarray] = None      # mascara del ROI
    contorno: Optional[np.ndarray] = None     # en coordenadas del fotograma completo


class DetectorLinea:
    def __init__(self, cfg):
        self.cfg = cfg
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    def detectar(self, frame) -> ResultadoLinea:
        cfg = self.cfg
        alto, ancho = frame.shape[:2]
        y0 = int(alto * cfg.roi_inicio)
        y1 = int(alto * getattr(cfg, "roi_fin", 1.0))
        roi = frame[y0:y1, :]

        gris = cv2.GaussianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        vacia = np.zeros(gris.shape, np.uint8)

        # Si el ROI es casi uniforme no hay linea (evita que Otsu invente una)
        p_bajo, p_alto = np.percentile(gris, (1, 99))
        if (p_alto - p_bajo) < cfg.contraste_minimo:
            return ResultadoLinea(False, y0=y0, mascara=vacia)

        tipo = cv2.THRESH_BINARY_INV if cfg.linea_oscura else cv2.THRESH_BINARY
        if cfg.umbral_linea > 0:
            _, mascara = cv2.threshold(gris, cfg.umbral_linea, 255, tipo)
        else:
            _, mascara = cv2.threshold(gris, 0, 255, tipo | cv2.THRESH_OTSU)

        # Quitar colores vivos (senales rojas/verdes)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        vivido = (hsv[:, :, 1] > cfg.saturacion_vivida) & (hsv[:, :, 2] > cfg.valor_vivido)
        mascara[vivido] = 0

        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, self._kernel)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, self._kernel)

        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return ResultadoLinea(False, y0=y0, mascara=mascara)

        mayor = max(contornos, key=cv2.contourArea)
        area = cv2.contourArea(mayor)
        area_rel = area / float(mascara.shape[0] * mascara.shape[1])
        if area_rel < cfg.area_minima_linea:
            return ResultadoLinea(False, area_rel=area_rel, y0=y0, mascara=mascara)

        m = cv2.moments(mayor)
        if m["m00"] == 0:
            return ResultadoLinea(False, y0=y0, mascara=mascara)
        cx = int(m["m10"] / m["m00"])
        cy = int(m["m01"] / m["m00"]) + y0
        error = (cx - ancho / 2.0) / (ancho / 2.0)

        mayor_global = mayor + np.array([[[0, y0]]], dtype=mayor.dtype)
        return ResultadoLinea(True, cx, cy, float(error), area_rel, y0, mascara, mayor_global)
