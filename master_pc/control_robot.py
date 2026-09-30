"""
control_robot.py - Clases ControladorRobot y RobotSimulado.

ControladorRobot envuelve la clase Robot ORIGINAL (Robot.py, sin modificar)
y traduce las acciones del algoritmo a sus metodos reales:
  adelante -> Robot.adelante()   izquierda -> Robot.izquierda()
  derecha  -> Robot.derecha()    parar     -> Robot.parar()
RobotSimulado tiene la misma interfaz pero no usa Bluetooth: sirve para
probar el algoritmo en cualquier PC sin el robot.
"""
import time


class RobotSimulado:
    """Misma interfaz que Robot, pero solo registra los comandos."""

    def __init__(self):
        self.historial = []
        self._ultimo = None

    def conectar(self):
        print("[SIMULADO] Robot simulado listo (no se usa Bluetooth).")

    def _reg(self, cmd):
        self.historial.append(cmd)
        if cmd != self._ultimo:
            print(f"[SIMULADO] comando: {cmd}")
            self._ultimo = cmd

    def adelante(self): self._reg("w")
    def atras(self): self._reg("s")
    def izquierda(self): self._reg("a")
    def derecha(self): self._reg("d")
    def parar(self): self._reg("x")
    def cerrar(self): print("[SIMULADO] cerrado.")


class ControladorRobot:
    INTERVALO_PARAR = 0.5   # s entre 'x' repetidos mientras esta detenido

    def __init__(self, cfg):
        self.cfg = cfg
        if cfg.simulado:
            self.robot = RobotSimulado()
        else:
            from Robot import Robot   # clase original del repositorio
            self.robot = Robot(cfg.mac, cfg.puerto_bt)
        self.conectado = False
        self._ultimo_parar = 0.0
        self._ultima_accion = None
        self._contador_frames = 0

    def conectar(self):
        self.robot.conectar()
        self.conectado = True

    def _traducir(self, accion):
        if self.cfg.invertir_giro:
            accion = {"izquierda": "derecha", "derecha": "izquierda"}.get(accion, accion)
        return accion

    def ejecutar(self, accion: str):
        self._contador_frames += 1
        accion_traducida = self._traducir(accion)
        intervalo = getattr(self.cfg, "intervalo_envio", 20)

        # Si la accion cambio o la parada es obligatoria, se envia de inmediato.
        # Si la accion es repetida, solo se envia cada N fotogramas (intervalo_envio).
        cambio_accion = (accion_traducida != self._ultima_accion)
        debe_enviar = cambio_accion or (self._contador_frames % intervalo == 0) or (accion_traducida == "parar")

        if not debe_enviar:
            return

        if accion_traducida == "parar":
            ahora = time.monotonic()
            if self._ultima_accion == "parar" and ahora - self._ultimo_parar < self.INTERVALO_PARAR:
                return
            self._ultimo_parar = ahora
            self.robot.parar()
        elif accion_traducida == "adelante":
            self.robot.adelante()
        elif accion_traducida == "izquierda":
            self.robot.izquierda()
        elif accion_traducida == "derecha":
            self.robot.derecha()
        else:
            raise ValueError(f"Accion desconocida: {accion_traducida}")
        self._ultima_accion = accion_traducida

    def parar_seguro(self):
        """Intenta detener el robot sin lanzar errores (para usar al salir)."""
        try:
            if self.conectado or self.cfg.simulado:
                self.robot.parar()
        except Exception:
            pass

    def cerrar(self):
        self.parar_seguro()
        try:
            self.robot.cerrar()
        except Exception:
            pass
        self.conectado = False
