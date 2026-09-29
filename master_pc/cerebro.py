"""
cerebro.py - Clase Cerebro: toma las decisiones.

Recibe lo que "ve" el robot (linea + senales) y devuelve UNA accion:
  'adelante' | 'izquierda' | 'derecha' | 'parar'

Maquina de estados:
  SIGUIENDO --(rojo confirmado)--> PARADO --(pasa tiempo_pare)--> SIGUIENDO
Tras reanudar se ignora el rojo hasta que deje de verse (o pase max_ignorar_rojo),
si no el robot se volveria a detener ante el mismo octagono.
El verde (SIGA) se confirma y se reporta; el robot continua siguiendo la linea.

Como el firmware mueve el robot en pulsos cortos (w = 100 ms, a/d = 30 ms),
el error moderado se corrige ALTERNANDO giro y avance para no perder progreso.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Estado(Enum):
    SIGUIENDO = "SIGUIENDO"
    PARADO = "PARADO (PARE)"


@dataclass
class Decision:
    accion: str
    estado: Estado
    evento: Optional[str] = None      # texto cuando ocurre algo notable
    detalle: str = ""                 # motivo de la accion (para el HUD)


class Cerebro:
    def __init__(self, cfg):
        self.cfg = cfg
        self.estado = Estado.SIGUIENDO
        self._t_parada = 0.0
        self._c_rojo = 0
        self._c_verde = 0
        self._verde_activo = False
        self._rojo_ignorado = False
        self._t_ignorar = 0.0
        self._sin_rojo = 0
        self._perdida = 0
        self._ultimo_error = 0.0
        self._alternar = False
        self.paradas = 0
        self.senales_siga = 0

    # ------------------------------------------------------------------
    def decidir(self, linea, senales, t: float) -> Decision:
        cfg = self.cfg
        rojo, verde = senales.get("rojo"), senales.get("verde")

        # Re-armado del PARE tras reanudar (primero, antes de contar)
        if self._rojo_ignorado:
            self._sin_rojo = 0 if rojo is not None else self._sin_rojo + 1
            if (self._sin_rojo >= cfg.frames_rearme
                    or t - self._t_ignorar >= cfg.max_ignorar_rojo):
                self._rojo_ignorado = False
                self._c_rojo = 0

        # Confirmacion por varios fotogramas (evita falsos positivos).
        # Contador "con fuga": un fotograma fallido resta 1 en vez de reiniciar,
        # asi el desenfoque de movimiento no impide confirmar la senal.
        # Tiene tope para que no quede "cargado" y dispare tarde.
        tope = 2 * cfg.frames_confirmacion
        rojo_grande = rojo is not None and rojo.area_rel >= cfg.area_min_senal
        verde_grande = verde is not None and verde.area_rel >= cfg.area_min_senal
        if self._rojo_ignorado:
            self._c_rojo = 0                      # no acumular mientras se ignora
        else:
            self._c_rojo = min(tope, self._c_rojo + 1) if rojo_grande else max(0, self._c_rojo - 1)
        self._c_verde = min(tope, self._c_verde + 1) if verde_grande else max(0, self._c_verde - 1)

        evento = None

        # ------------------ Estado PARADO ------------------
        if self.estado is Estado.PARADO:
            restante = cfg.tiempo_pare - (t - self._t_parada)
            if restante > 0:
                return Decision("parar", self.estado, None, f"PARE: faltan {restante:.1f}s")
            self.estado = Estado.SIGUIENDO
            self._rojo_ignorado = True
            self._t_ignorar = t
            self._sin_rojo = 0
            self._c_rojo = 0
            evento = "Tiempo de PARE cumplido: reanudando"

        # ------------------ Estado SIGUIENDO ------------------
        if rojo_grande and self._c_rojo >= cfg.frames_confirmacion and not self._rojo_ignorado:
            self.estado = Estado.PARADO
            self._t_parada = t
            self.paradas += 1
            return Decision("parar", self.estado, "SENAL PARE detectada: deteniendo",
                            f"PARE: faltan {cfg.tiempo_pare:.1f}s")

        if verde_grande and self._c_verde >= cfg.frames_confirmacion:
            if not self._verde_activo:
                self._verde_activo = True
                self.senales_siga += 1
                evento = "SENAL SIGA detectada: continuando"
        elif verde is None:
            self._verde_activo = False

        accion, detalle = self._seguir_linea(linea)
        return Decision(accion, self.estado, evento, detalle)

    # ------------------------------------------------------------------
    def _seguir_linea(self, linea):
        cfg = self.cfg
        if not linea.visible:
            self._perdida += 1
            if self._perdida <= cfg.frames_busqueda:
                lado = "izquierda" if self._ultimo_error < 0 else "derecha"
                return lado, f"linea perdida: buscando a la {lado}"
            return "parar", "linea perdida: detenido"

        self._perdida = 0
        self._ultimo_error = linea.error
        e = abs(linea.error)
        lado = "izquierda" if linea.error < 0 else "derecha"

        if e <= cfg.zona_muerta:
            self._alternar = False
            return "adelante", f"centrada (e={linea.error:+.2f})"
        if e >= cfg.giro_fuerte:
            self._alternar = False
            return lado, f"giro fuerte (e={linea.error:+.2f})"
        # error moderado: alternar giro / avance
        self._alternar = not self._alternar
        if self._alternar:
            return lado, f"correccion (e={linea.error:+.2f})"
        return "adelante", f"avance corrigiendo (e={linea.error:+.2f})"
