"""
camara.py - Clase Camara.

Lee video de una webcam, de la camara IP del celular o de un archivo.
Para camaras en vivo usa un hilo que siempre conserva el ULTIMO fotograma:
asi el algoritmo nunca procesa imagenes viejas acumuladas en el buffer de
red (esa demora hace que el robot reaccione tarde).
"""
import os
import threading
import time

import cv2


class Camara:
    def __init__(self, fuente, ancho: int, alto: int, rotacion: int = 0):
        self.fuente_txt = str(fuente)
        self.ancho = ancho
        self.alto = alto
        self.rotacion = rotacion
        self.es_archivo = os.path.isfile(self.fuente_txt)
        self._src = int(self.fuente_txt) if self.fuente_txt.isdigit() else self.fuente_txt
        self.fps = 30.0
        self.terminada = False       # True cuando un archivo de video se acabo

        self._cap = None
        self._frame = None
        self._lock = threading.Lock()
        self._nuevo = threading.Event()
        self._activo = False
        self._hilo = None

    def _abrir(self):
        cap = cv2.VideoCapture(self._src)
        if cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except cv2.error:
                pass
            return cap
        cap.release()
        return None

    def iniciar(self):
        self._cap = self._abrir()
        if self._cap is None:
            raise RuntimeError(
                f"No se pudo abrir la fuente de video: {self.fuente_txt}\n"
                "  - Celular: revisa que la app de camara IP este transmitiendo y que "
                "el PC y el celular esten en la misma red WiFi.\n"
                "  - Webcam: prueba --fuente 0, 1, 2 ...")
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        if fps and 1 < fps < 240:
            self.fps = float(fps)
        if not self.es_archivo:
            self._activo = True
            self._hilo = threading.Thread(target=self._bucle, daemon=True)
            self._hilo.start()

    def _bucle(self):
        fallos = 0
        while self._activo:
            ok, frame = self._cap.read()
            if ok and frame is not None:
                fallos = 0
                with self._lock:
                    self._frame = frame
                    self._nuevo.set()
            else:
                fallos += 1
                time.sleep(0.05)
                if fallos >= 40:  # ~2 s sin video: reconectar
                    self._cap.release()
                    while self._activo:
                        cap = self._abrir()
                        if cap is not None:
                            self._cap = cap
                            break
                        time.sleep(1.0)
                    fallos = 0

    def leer(self, timeout: float = 1.0):
        """Devuelve (ok, fotograma_redimensionado)."""
        if self.es_archivo:
            ok, frame = self._cap.read()
            if not ok:
                self.terminada = True
                return False, None
        else:
            if not self._nuevo.wait(timeout):
                return False, None
            with self._lock:
                self._nuevo.clear()
                frame = self._frame
            if frame is None:
                return False, None
        if self.rotacion in (90, "90"):
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotacion in (180, "180"):
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotacion in (270, -90, "-90"):
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return True, cv2.resize(frame, (self.ancho, self.alto))

    def liberar(self):
        self._activo = False
        if self._hilo is not None:
            self._hilo.join(timeout=1.5)
        if self._cap is not None:
            self._cap.release()
