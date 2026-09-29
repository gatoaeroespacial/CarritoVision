"""
visualizacion.py - Clase Visualizador: dibuja lo que el algoritmo esta "viendo".
(Los textos usan solo ASCII porque las fuentes de OpenCV no dibujan tildes.)
"""
import cv2
import numpy as np

COLORES = {"rojo": (0, 0, 255), "verde": (0, 200, 0)}


class Visualizador:
    def __init__(self, cfg):
        self.cfg = cfg

    def dibujar(self, frame, linea, senales, decision, fps, pausado=False):
        img = frame.copy()
        alto, ancho = img.shape[:2]
        centro = ancho // 2
        y0 = linea.y0

        # ROI y zona muerta
        cv2.rectangle(img, (0, y0), (ancho - 1, alto - 1), (255, 255, 0), 1)
        zm = int(self.cfg.zona_muerta * ancho / 2)
        cv2.line(img, (centro - zm, y0), (centro - zm, alto), (200, 200, 0), 1)
        cv2.line(img, (centro + zm, y0), (centro + zm, alto), (200, 200, 0), 1)
        cv2.line(img, (centro, y0), (centro, alto), (255, 255, 255), 1)

        # Linea
        if linea.visible:
            cv2.drawContours(img, [linea.contorno], -1, (0, 255, 255), 2)
            cv2.circle(img, (linea.cx, linea.cy), 7, (255, 0, 255), -1)
            cv2.line(img, (centro, linea.cy), (linea.cx, linea.cy), (255, 0, 255), 2)

        # Senales
        for nombre, s in senales.items():
            if s is None:
                continue
            x, y, w, h = s.bbox
            col = COLORES[nombre]
            cv2.rectangle(img, (x, y), (x + w, y + h), col, 2)
            etiqueta = "PARE" if nombre == "rojo" else "SIGA"
            cv2.putText(img, f"{etiqueta} {s.area_rel * 100:.1f}%", (x, max(15, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)

        # Panel de texto
        cv2.rectangle(img, (0, 0), (ancho, 62), (0, 0, 0), -1)
        estado = "PAUSA MANUAL" if pausado else decision.estado.value
        cv2.putText(img, f"Estado: {estado}   Accion: {decision.accion.upper()}", (8, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, f"{decision.detalle}   FPS:{fps:4.1f}", (8, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        return img

    @staticmethod
    def mascara_a_bgr(linea, ancho, alto):
        """Mascara del ROI colocada en un lienzo del tamano del fotograma."""
        lienzo = np.zeros((alto, ancho), np.uint8)
        if linea.mascara is not None:
            lienzo[linea.y0:alto, :] = linea.mascara
        return cv2.cvtColor(lienzo, cv2.COLOR_GRAY2BGR)
