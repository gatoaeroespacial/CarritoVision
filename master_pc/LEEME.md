# Reto 1 - Robot seguidor de linea (PARE rojo / SIGA verde)

Todo el codigo esta en `master_pc/`. `Robot.py` es el ORIGINAL del repositorio
(sin cambios) y NO se toca el Arduino: el programa solo envia w/a/d/s/x.

## Instalacion
    pip install -r requirements.txt

## Estructura (una clase por archivo)
    config.py            Configuracion  -> todos los parametros ajustables
    camara.py            Camara         -> webcam / celular (URL) / video, siempre el ultimo fotograma
    detector_linea.py    DetectorLinea  -> ROI, gris, Otsu, morfologia, contornos, centroide, error
    detector_senales.py  DetectorSenales-> HSV, inRange, morfologia, contornos, approxPolyDP (octagonos)
    cerebro.py           Cerebro        -> maquina de estados SIGUIENDO / PARADO y decision de la accion
    control_robot.py     ControladorRobot y RobotSimulado -> envuelven Robot.py
    visualizacion.py     Visualizador   -> dibuja lo que "ve" el algoritmo
    main.py              AplicacionReto -> une todo (punto de entrada)
    herramientas/        generar_video_prueba.py, calibrar_hsv.py
    tests/               test_reto1.py

## Orden recomendado de pruebas
1. Pruebas automaticas:       python -m unittest discover -s tests -v
2. Video de prueba, sin robot: python main.py --fuente prueba.mp4 --simulado --tiempo-pare 2
   (si falta prueba.mp4:      python herramientas/generar_video_prueba.py prueba.mp4)
3. Videos de ensayo del docente, sin robot:
                              python main.py --fuente ruta/al/video.mp4 --simulado
4. Celular, sin robot:        python main.py --fuente http://IP_DEL_CELULAR:8080/video --simulado
   (abre primero esa URL en el navegador del PC: si ahi se ve el video, aqui tambien)
5. Robot real (primero con las ruedas en el aire):
                              python main.py --fuente http://IP:8080/video --mac AA:BB:CC:DD:EE:FF

Teclas: q = salir | ESPACIO = pausa manual (parada de seguridad)

## Si algo no sale igual con la pista real
- El robot gira al reves            -> agrega --invertir-giro
- Linea clara sobre piso oscuro     -> agrega --linea-clara
- No detecta la linea               -> revisa la ventana "Mascara de la linea"; prueba --umbral 90 (o --roi 0.45)
- No detecta/actua tarde ante el octagono -> mira el % que muestra el cuadro de la senal y ajusta --area-senal
- Colores rojo/verde no se detectan -> python herramientas/calibrar_hsv.py --fuente URL
                                       y pega los rangos con la tecla 's' en config.py (rojo_a, rojo_b, verde)
- Tiempo del PARE definido por el docente -> --tiempo-pare SEGUNDOS
- Guardar video para el poster      -> --guardar-video salida.mp4
