"""
main.py - Reto 1: robot seguidor de linea con octagonos PARE (rojo) / SIGA (verde).

Ejemplos (ejecutar desde la carpeta master_pc):
  python main.py --fuente prueba.mp4 --simulado                 # sin robot, con video
  python main.py --fuente http://IP:8080/video --simulado       # celular, sin robot
  python main.py --fuente http://IP:8080/video --mac AA:BB:...  # celular + robot real

Teclas: q = salir | ESPACIO = pausa/reanudar (parada manual segura)
NOTA: este programa NO modifica el Arduino; solo envia w/a/d/s/x con Robot.py.
"""
import argparse
import signal
import sys
import time

import cv2

from camara import Camara
from cerebro import Cerebro
from config import Configuracion
from control_robot import ControladorRobot
from detector_linea import DetectorLinea
from detector_senales import DetectorSenales
from visualizacion import Visualizador


class AplicacionReto:
    def __init__(self, cfg: Configuracion):
        self.cfg = cfg
        self.camara = Camara(cfg.fuente, cfg.ancho, cfg.alto)
        self.linea = DetectorLinea(cfg)
        self.senales = DetectorSenales(cfg)
        self.cerebro = Cerebro(cfg)
        self.robot = ControladorRobot(cfg)
        self.vista = Visualizador(cfg)
        self.pausado = False
        self._n = 0
        self._t0 = time.monotonic()
        self._fps = 0.0
        self._escritor = None

    def _ahora(self) -> float:
        """Reloj de decision. En video de archivo usa el tiempo del video
        (asi el PARE dura lo mismo aunque se procese mas rapido/lento)."""
        if self.camara.es_archivo:
            return self._n / self.camara.fps
        return time.monotonic() - self._t0

    def _guardar(self, img):
        if not self.cfg.guardar_video:
            return
        if self._escritor is None:
            fps = self.camara.fps if self.camara.es_archivo else 10.0
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._escritor = cv2.VideoWriter(self.cfg.guardar_video, fourcc, fps,
                                             (img.shape[1], img.shape[0]))
        self._escritor.write(img)

    def ejecutar(self) -> int:
        # Que cerrar la terminal (SIGTERM) tambien detenga el robot con seguridad
        def _terminar(*_):
            raise KeyboardInterrupt
        try:
            signal.signal(signal.SIGTERM, _terminar)
        except (ValueError, AttributeError):
            pass
        self.camara.iniciar()
        self.robot.conectar()
        print("Corriendo. Teclas: 'q' salir, ESPACIO pausa. (Ctrl+C tambien detiene el robot)")
        fallos = 0
        t_prev = time.monotonic()
        codigo = 0
        try:
            while True:
                ok, frame = self.camara.leer()
                if not ok:
                    if self.camara.terminada:
                        print("Fin del video.")
                        break
                    fallos += 1
                    self.robot.ejecutar("parar")          # sin video => robot quieto
                    print(f"Sin imagen ({fallos}/{self.cfg.max_fallos_camara})")
                    if fallos >= self.cfg.max_fallos_camara:
                        print("Camara perdida: abortando por seguridad.")
                        codigo = 1
                        break
                    continue
                fallos = 0
                self._n += 1

                linea = self.linea.detectar(frame)
                senales = self.senales.detectar(frame)
                decision = self.cerebro.decidir(linea, senales, self._ahora())
                if decision.evento:
                    print(f"[{self._ahora():6.2f}s] {decision.evento}")

                self.robot.ejecutar("parar" if self.pausado else decision.accion)

                ahora = time.monotonic()
                dt = max(ahora - t_prev, 1e-6)
                self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt
                t_prev = ahora

                if self.cfg.ventana or self.cfg.guardar_video:
                    img = self.vista.dibujar(frame, linea, senales, decision, self._fps, self.pausado)
                    self._guardar(img)
                    if self.cfg.ventana:
                        cv2.imshow("Reto 1 - Vision", img)
                        cv2.imshow("Mascara de la linea",
                                   self.vista.mascara_a_bgr(linea, self.cfg.ancho, self.cfg.alto))
                        tecla = cv2.waitKey(1) & 0xFF
                        if tecla == ord("q"):
                            break
                        if tecla == 32:
                            self.pausado = not self.pausado
                            print("PAUSA MANUAL" if self.pausado else "Reanudado")
        except KeyboardInterrupt:
            print("Interrumpido por el usuario.")
        except (OSError, RuntimeError) as e:
            print(f"Error de comunicacion con el robot: {e}")
            codigo = 1
        finally:
            self.robot.cerrar()          # siempre envia 'x' y cierra Bluetooth
            self.camara.liberar()
            if self._escritor is not None:
                self._escritor.release()
            cv2.destroyAllWindows()
            print(f"Resumen: {self._n} fotogramas | PAREs cumplidos/iniciados: "
                  f"{self.cerebro.paradas} | SIGA detectados: {self.cerebro.senales_siga}")
        return codigo


def leer_argumentos() -> Configuracion:
    c = Configuracion()
    p = argparse.ArgumentParser(description="Reto 1: seguidor de linea con vision artificial")
    p.add_argument("--fuente", default=c.fuente, help="0, URL del celular o archivo de video")
    p.add_argument("--mac", default=c.mac, help="MAC Bluetooth del mBot")
    p.add_argument("--simulado", action="store_true", help="no usar el robot, solo imprimir comandos")
    p.add_argument("--invertir-giro", action="store_true", help="si el robot gira al reves")
    p.add_argument("--linea-clara", action="store_true", help="linea clara sobre piso oscuro")
    p.add_argument("--umbral", type=int, default=c.umbral_linea, help="umbral fijo (0 = Otsu)")
    p.add_argument("--roi", type=float, default=c.roi_inicio, help="inicio vertical del ROI (0-1)")
    p.add_argument("--tiempo-pare", type=float, default=c.tiempo_pare, help="segundos de PARE")
    p.add_argument("--area-senal", type=float, default=c.area_min_senal,
                   help="area minima (fraccion del fotograma) para actuar ante una senal")
    p.add_argument("--sin-ventana", action="store_true", help="sin interfaz grafica")
    p.add_argument("--guardar-video", default="", help="guardar el video anotado (ej. salida.mp4)")
    a = p.parse_args()

    c.fuente, c.mac, c.simulado = a.fuente, a.mac, a.simulado
    c.invertir_giro, c.linea_oscura = a.invertir_giro, not a.linea_clara
    c.umbral_linea, c.roi_inicio = a.umbral, a.roi
    c.tiempo_pare, c.area_min_senal = a.tiempo_pare, a.area_senal
    c.ventana, c.guardar_video = not a.sin_ventana, a.guardar_video
    return c


if __name__ == "__main__":
    try:
        sys.exit(AplicacionReto(leer_argumentos()).ejecutar())
    except RuntimeError as e:      # camara que no abre, etc.
        print(f"ERROR: {e}")
        sys.exit(1)
