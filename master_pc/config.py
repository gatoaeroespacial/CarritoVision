"""
config.py - Parametros ajustables del Reto 1 en un solo lugar.

Si algo no funciona con la luz real de la pista, casi siempre se
arregla cambiando un valor de este archivo (o con los argumentos de main.py),
NUNCA tocando el Arduino.
"""
from dataclasses import dataclass


@dataclass
class Configuracion:
    # ---------------- Fuente de video ----------------
    fuente: str = "0"            # "0" = webcam, URL del celular, o ruta a un video .mp4
    ancho: int = 640             # todos los fotogramas se redimensionan a este tamano
    alto: int = 480
    max_fallos_camara: int = 5   # fotogramas fallidos seguidos antes de abortar

    # ---------------- Robot (Bluetooth) ----------------
    mac: str = "00:1B:10:21:2C:1B"   # <-- CAMBIAR por la MAC real del mBot
    puerto_bt: int = 1
    simulado: bool = False       # True = no envia nada al robot, solo imprime comandos
    invertir_giro: bool = False  # True si el robot gira al reves de lo esperado

    # ---------------- Deteccion de la linea ----------------
    linea_oscura: bool = True    # True = linea negra sobre piso claro
    roi_inicio: float = 0.55     # la linea se busca en el 45 % inferior de la imagen
    umbral_linea: int = 0        # 0 = umbral automatico (Otsu); 1-254 = umbral fijo
    contraste_minimo: int = 40   # si la zona es casi uniforme se asume "sin linea"
    area_minima_linea: float = 0.004   # fraccion minima del ROI para aceptar la linea
    saturacion_vivida: int = 110       # pixeles muy coloridos (senales) NO son linea
    valor_vivido: int = 90

    # ---------------- Control de direccion ----------------
    zona_muerta: float = 0.12    # |error| menor a esto => avanzar recto
    giro_fuerte: float = 0.45    # |error| mayor a esto => solo girar (sin avanzar)
    frames_busqueda: int = 12    # fotogramas girando hacia el ultimo lado si se pierde la linea

    # ---------------- Senales (octagonos) ----------------
    tiempo_pare: float = 5.0     # segundos detenido en PARE (lo define el docente)
    area_min_senal: float = 0.012      # fraccion del fotograma para "actuar" ante la senal
    area_min_deteccion: float = 0.002  # fraccion minima para dibujarla/mostrarla
    frames_confirmacion: int = 3       # fotogramas seguidos para confirmar una senal
    frames_rearme: int = 5             # fotogramas sin ver rojo para volver a armar el PARE
    max_ignorar_rojo: float = 8.0      # s maximos ignorando el rojo tras reanudar

    # Rangos HSV (OpenCV: H 0-179, S 0-255, V 0-255). Rojo necesita 2 rangos.
    rojo_a: tuple = ((0, 120, 70), (10, 255, 255))
    rojo_b: tuple = ((170, 120, 70), (179, 255, 255))
    verde: tuple = ((40, 80, 50), (85, 255, 255))

    # ---------------- Salida ----------------
    ventana: bool = True
    guardar_video: str = ""
