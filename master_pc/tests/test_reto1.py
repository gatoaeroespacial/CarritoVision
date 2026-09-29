"""
Pruebas automaticas (no necesitan robot, camara ni pantalla).
Ejecutar desde master_pc:   python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from cerebro import Cerebro, Estado                      # noqa: E402
from config import Configuracion                         # noqa: E402
from control_robot import ControladorRobot               # noqa: E402
from detector_linea import DetectorLinea, ResultadoLinea  # noqa: E402
from detector_senales import DetectorSenales             # noqa: E402


def piso():
    return np.full((480, 640, 3), 205, np.uint8)


def con_linea(x):
    img = piso()
    cv2.line(img, (x, 480), (x, 200), (25, 25, 25), 34)
    return img


def octagono(img, c, r, color):
    pts = [(int(c[0] + r * np.cos(np.radians(22.5 + 45 * k))),
            int(c[1] + r * np.sin(np.radians(22.5 + 45 * k)))) for k in range(8)]
    cv2.fillPoly(img, [np.array(pts, np.int32)], color)


class SocketFalso:
    def __init__(self):
        self.enviado = b""

    def sendall(self, datos):
        self.enviado += datos

    def close(self):
        pass


class PruebasLinea(unittest.TestCase):
    def setUp(self):
        self.det = DetectorLinea(Configuracion())

    def test_izquierda(self):
        r = self.det.detectar(con_linea(120))
        self.assertTrue(r.visible)
        self.assertLess(r.error, -0.5)

    def test_derecha(self):
        r = self.det.detectar(con_linea(520))
        self.assertTrue(r.visible)
        self.assertGreater(r.error, 0.5)

    def test_centro(self):
        r = self.det.detectar(con_linea(320))
        self.assertLess(abs(r.error), 0.05)

    def test_sin_linea(self):
        self.assertFalse(self.det.detectar(piso()).visible)

    def test_octagono_rojo_no_es_linea(self):
        img = piso()
        octagono(img, (320, 400), 60, (30, 30, 200))
        self.assertFalse(self.det.detectar(img).visible)


class PruebasSenales(unittest.TestCase):
    def setUp(self):
        self.det = DetectorSenales(Configuracion())

    def test_rojo(self):
        img = piso(); octagono(img, (500, 200), 50, (30, 30, 200))
        s = self.det.detectar(img)
        self.assertIsNotNone(s["rojo"]); self.assertIsNone(s["verde"])

    def test_verde(self):
        img = piso(); octagono(img, (150, 200), 50, (40, 170, 40))
        s = self.det.detectar(img)
        self.assertIsNotNone(s["verde"]); self.assertIsNone(s["rojo"])

    def test_cuadrado_rojo_se_rechaza(self):
        img = piso(); cv2.rectangle(img, (400, 100), (500, 200), (30, 30, 200), -1)
        self.assertIsNone(self.det.detectar(img)["rojo"])

    def test_circulo_rojo_se_rechaza(self):
        img = piso(); cv2.circle(img, (400, 200), 50, (30, 30, 200), -1)
        self.assertIsNone(self.det.detectar(img)["rojo"])


class PruebasCerebro(unittest.TestCase):
    def linea(self, e):
        return ResultadoLinea(True, 0, 0, e, 0.1)

    def test_direcciones(self):
        c = Cerebro(Configuracion())
        sin = {"rojo": None, "verde": None}
        self.assertEqual(c.decidir(self.linea(0.0), sin, 0).accion, "adelante")
        self.assertEqual(c.decidir(self.linea(-0.9), sin, 0.1).accion, "izquierda")
        self.assertEqual(c.decidir(self.linea(0.9), sin, 0.2).accion, "derecha")

    def test_pare_dura_lo_configurado_y_no_repite(self):
        from detector_senales import Senal
        cfg = Configuracion(tiempo_pare=2.0)
        c = Cerebro(cfg)
        rojo = Senal("rojo", 0.05, (0, 0, 10, 10), 8, None)
        sin = {"rojo": None, "verde": None}
        con = {"rojo": rojo, "verde": None}
        t, paro_desde, reanudo = 0.0, None, None
        for i in range(400):
            t = i / 30.0
            d = c.decidir(self.linea(0.0), con if 10 <= i < 150 else sin, t)
            if d.estado is Estado.PARADO and paro_desde is None:
                paro_desde = t
            if paro_desde is not None and reanudo is None and d.estado is Estado.SIGUIENDO:
                reanudo = t
        self.assertAlmostEqual(reanudo - paro_desde, 2.0, delta=0.1)
        self.assertEqual(c.paradas, 1)

    def test_linea_perdida_busca_y_luego_para(self):
        cfg = Configuracion()
        c = Cerebro(cfg)
        sin = {"rojo": None, "verde": None}
        c.decidir(self.linea(-0.8), sin, 0)
        perdida = ResultadoLinea(False)
        self.assertEqual(c.decidir(perdida, sin, 0.1).accion, "izquierda")
        for i in range(cfg.frames_busqueda + 2):
            d = c.decidir(perdida, sin, 0.2 + i)
        self.assertEqual(d.accion, "parar")


class PruebasRobotReal(unittest.TestCase):
    """Usa la clase Robot ORIGINAL con un socket falso: verifica los bytes enviados."""

    def test_comandos(self):
        ctrl = ControladorRobot(Configuracion(simulado=False))
        falso = SocketFalso()
        ctrl.robot.bluetooth_socket = falso
        ctrl.conectado = True
        for accion in ("adelante", "izquierda", "derecha", "parar"):
            ctrl.ejecutar(accion)
        self.assertEqual(falso.enviado, b"wadx")

    def test_invertir_giro(self):
        ctrl = ControladorRobot(Configuracion(invertir_giro=True))
        falso = SocketFalso()
        ctrl.robot.bluetooth_socket = falso
        ctrl.conectado = True
        ctrl.ejecutar("izquierda"); ctrl.ejecutar("derecha")
        self.assertEqual(falso.enviado, b"da")

    def test_cerrar_envia_parar(self):
        ctrl = ControladorRobot(Configuracion())
        falso = SocketFalso()
        ctrl.robot.bluetooth_socket = falso
        ctrl.conectado = True
        ctrl.cerrar()
        self.assertEqual(falso.enviado, b"x")


if __name__ == "__main__":
    unittest.main()
