# Comunicación digital inalámbrica GFSK con Raspberry Pi Pico 2W y nRF24L01

Informe de laboratorio (décimo informe) de **Comunicaciones Digitales**, Universidad Militar Nueva Granada (UMNG), Programa de Ingeniería en Telecomunicaciones, periodo 2026-2.

- **Autores:** Riveros Sierra Harol Felipe (1401660) y Bohorquez Blanco Salome (1401654)
- **Docente:** Ing. José de Jesús Rugeles Uribe
- **Informe:** `DECIMO INFORME .docx` (y su versión en PDF, `DECIMO INFORME .pdf`), incluidos en este repositorio

## ¿De qué trata?

Se implementó un enlace inalámbrico con modulación **GFSK** en la banda de 2,4 GHz usando dos tarjetas **Raspberry Pi Pico 2W** y dos módulos **nRF24L01**, y se evaluó así:

| Parte | Qué se hizo |
|---|---|
| 4.1 Análisis de SPI | Captura y decodificación con analizador lógico de la lectura de registros, la escritura del canal (RF_CH) y la carga de un paquete. |
| 4.2 Alcance | Cálculo teórico en espacio libre y prueba de campo para 3 velocidades y 4 potencias. |
| 4.3 Errores | Medición de la tasa de error de bits (BER) enviando un archivo de alfabetos y otro pseudoaleatorio. |
| 4.4 Espectro | Verificación de la frecuencia, ancho de banda y espectrograma con un analizador de espectros Anritsu MS2724B. |

## Hardware

- 2 × Raspberry Pi Pico 2W (una transmisora y una receptora)
- 2 × módulo nRF24L01
- 2 × pantalla OLED SSD1306 de 128×64 (I2C)
- 3 pulsadores y LEDs por tarjeta
- Analizador lógico (parte 4.1) y analizador de espectros (parte 4.4)

### Conexiones (iguales en las dos tarjetas)

| Función | Pin de la Pico |
|---|---|
| OLED SDA / SCL (I2C0) | GP4 / GP5 |
| nRF24L01 SCK / MOSI / MISO (SPI0) | GP18 / GP19 / GP16 |
| nRF24L01 CSN / CE | GP17 / GP20 |
| Pulsadores (con pull-up interno, al GND) | GP10, GP11, GP12 |
| LED verde / LED de error | GP21 / GP22 (el de error solo en el transmisor de 4.2) |

El bus SPI trabaja a 1 MHz (modo 0).

## Contenido del repositorio

```
DECIMO INFORME .docx        Informe completo (Word)
DECIMO INFORME .pdf         Informe completo (PDF)
parte 4.2/   Prueba de alcance
  main_alcance_tx.py        Transmisor
  main_alcance_rx.py        Receptor
  nrf24 (3).py              Driver del nRF24L01
  parte 4.2.xlsx            Tabla de resultados de campo
  (32 fotos)                Pantallas OLED del transmisor y del receptor en cada prueba, y las consolas de Thonny
parte 4.3/   Prueba de BER
  main_ber_tx.py            Transmisor
  main_ber_rx.py            Receptor
  nrf24 (3).py              Driver del nRF24L01
  alfabetos.txt             Archivo de alfabetos (5600 bytes)
  aleatorio.txt             Archivo pseudoaleatorio (5600 bytes)
  parte 4.3.xlsx            Tabla de resultados de BER
  (9 fotos)                 Pantallas OLED del receptor y las consolas de Thonny
parte 4.4/   Análisis de espectro
  main_espectro_tx.py       Transmisor (modos CW, Paquetes y Barrido)
  nrf24 (3).py              Driver del nRF24L01
  Video de comprobacion de que se estaba transmitiendo.mp4
  (7 fotos)                 Analizador de espectros, montaje, frecuencia, ancho de banda y espectrograma
```



## Cómo ejecutar

1. Instala MicroPython en las dos Pico.
2. Copia a **cada** Pico `nrf24.py` y el driver `ssd1306.py` de MicroPython (este último no está en el repositorio).
3. En la parte 4.3 copia además `alfabetos.txt` y `aleatorio.txt` a las dos Pico.
4. Sube `main_..._tx.py` a una Pico y `main_..._rx.py` a la otra, y ejecútalos (por ejemplo, desde Thonny).
5. Las dos tarjetas deben quedar con **el mismo canal, velocidad y potencia**. El canal es el 76 (2476 MHz), por encima de los canales Wi-Fi 1, 6 y 11.

### Controles

| Parte | GP10 | GP11 | GP12 |
|---|---|---|---|
| 4.2 y 4.3 | Cambia la velocidad (250 kbps, 1 Mbps, 2 Mbps) | Cambia la potencia (−18, −12, −6, 0 dBm) | Solo en el transmisor: inicia la prueba (4.2) o envía los dos archivos (4.3) |
| 4.4 | Elige el ajuste (modo, canal, potencia, velocidad) | Cambia el valor del ajuste | Inicia o detiene la transmisión |

La pantalla OLED muestra el canal, la velocidad, la potencia y el resultado de la prueba. La consola de Thonny muestra el resumen final.

## Cómo funcionan las pruebas

- **Alcance (4.2):** el transmisor envía 100 paquetes de 32 bytes con ACK y cuenta los confirmados, los entregados al primer intento y los reintentos. El receptor cuenta cuántos paquetes le llegaron.
- **BER (4.3):** se desactivan el ACK y el CRC. Cada archivo se envía en 200 paquetes (4 bytes de cabecera y 28 de datos) y se repite 3 veces, para 600 paquetes. El receptor compara cada paquete con su copia del archivo y cuenta los bits erróneos, las cabeceras malas y los paquetes perdidos.
- **Espectro (4.4):** el transmisor emite una señal continua en el modo «Paquetes» para medirla con el analizador.

## Resultados principales

- **Alcance teórico:** de 15,3 m (2 Mbps, −18 dBm) a 483,7 m (250 kbps, 0 dBm).
- **Alcance en campo:** a distancias de 6 m a 62 m, la mayoría de las pruebas con 0, −6 y −12 dBm confirmó entre 94 y 100 de 100 paquetes. Con −18 dBm el enlace se degradó.
- **BER:** entre 0 y 3,7×10⁻³, sin tendencia clara con la potencia y con errores concentrados en pocos paquetes.
- **Espectro:** portadora en 2,476 GHz (canal 76) y ancho de banda de aproximadamente 1,5 MHz medido a 17,9 dB del pico.

Los detalles, las tablas y las fotos de cada prueba están en el informe (`DECIMO INFORME .docx` o `.pdf`).
