# main_espectro_tx.py -> cualquiera de las dos Pico, para el analizador de espectros (4.4)
# Necesita en la Pico: nrf24.py (versión nueva) y ssd1306.py
# Botones: GP10 = siguiente ajuste, GP11 = cambiar el valor, GP12 = iniciar/detener
# Modos: CW (portadora sin modular), Paquetes (señal GFSK continua), Barrido (salta de canal)
from machine import Pin, SPI, I2C
import time
import random
import ssd1306
from nrf24 import (NRF24, RATES, POWER_DBM, RF_SETUP, TX_ADDR, ADDRESS, STATUS,
                   W_TX_PAYLOAD, FLUSH_TX)
from nrf24 import _RATE_BITS
try:
    from os import urandom
except ImportError:
    urandom = None

# ---------- Configuración ----------
CANALES     = [2, 12, 22, 37, 40, 41, 42, 43, 62, 76, 83]   # canales que recorre el botón
BARRIDO_MAX = 83      # el modo Barrido va de 0 a este canal
PASO_MS     = 40      # milisegundos en cada canal en el modo Barrido
MODOS       = ("CW", "Paquetes", "Barrido")

# ---------- Hardware ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
idx_canal = CANALES.index(40)
radio = NRF24(spi, csn=17, ce=20, channel=CANALES[idx_canal], power=3, rate=1,
              auto_ack=False, crc=False)

btn_sel = Pin(10, Pin.IN, Pin.PULL_UP)
btn_chg = Pin(11, Pin.IN, Pin.PULL_UP)
btn_go  = Pin(12, Pin.IN, Pin.PULL_UP)
led_on  = Pin(21, Pin.OUT)


def pressed(pin):
    if pin.value() == 0:
        time.sleep_ms(30)
        if pin.value() == 0:
            while pin.value() == 0:
                time.sleep_ms(10)
            return True
    return False


def set_rate(r):
    radio.rate = r
    radio._write_rf_setup()


soportadas = [1, 2]
set_rate(0)
if radio.read_reg(RF_SETUP)[0] & 0x20:
    soportadas = [0, 1, 2]
set_rate(1)
idx_rate = soportadas.index(1)

modo = 1              # 0 CW, 1 Paquetes, 2 Barrido
sel = 0               # ajuste seleccionado: 0 modo, 1 canal, 2 potencia, 3 velocidad
activo = False
modo_activo = 1
barrido_ch = 0
t_ch = time.ticks_ms()


def datos():
    if urandom:
        return urandom(32)
    return bytes(random.getrandbits(8) for _ in range(32))


# ---------- Portadora continua (procedimiento de la librería RF24) ----------
def cw_on():
    radio.ce.value(0)
    radio.write_reg(RF_SETUP, _RATE_BITS[radio.rate] | (radio.power << 1) | 0x90)  # CONT_WAVE + PLL_LOCK
    radio._cmd(FLUSH_TX)
    radio.write_reg(TX_ADDR, b"\xFF\xFF\xFF\xFF\xFF")
    radio._cmd(W_TX_PAYLOAD, b"\xFF" * 32)
    radio.ce.value(1)
    time.sleep_us(1000)
    radio.ce.value(0)
    radio._cmd(0xE3)                       # REUSE_TX_PL
    radio.ce.value(1)
    time.sleep_us(1000)


def cw_off():
    radio.ce.value(0)
    radio._cmd(FLUSH_TX)
    radio.write_reg(TX_ADDR, ADDRESS)
    radio._write_rf_setup()
    radio.write_reg(STATUS, 0x70)


def iniciar():
    global activo, modo_activo, barrido_ch, t_ch
    modo_activo = modo
    radio.ce.value(0)
    if modo == 0:
        radio.set_channel(CANALES[idx_canal])
        cw_on()
    elif modo == 1:
        radio.set_channel(CANALES[idx_canal])
    else:
        barrido_ch = 0
        radio.set_channel(0)
        t_ch = time.ticks_ms()
    activo = True
    led_on.value(1)


def detener():
    global activo
    if modo_activo == 0:
        cw_off()
    radio.ce.value(0)
    radio.set_channel(CANALES[idx_canal])
    activo = False
    led_on.value(0)


def show():
    oled.fill(0)
    oled.text("ESPECTRO  %s" % ("ON" if activo else "OFF"), 0, 0)
    filas = (("Modo", MODOS[modo]),
             ("Canal", "%d" % CANALES[idx_canal]),
             ("Pot", "%d dBm" % POWER_DBM[radio.power]),
             ("Vel", RATES[radio.rate]))
    for i, (a, b) in enumerate(filas):
        oled.text(("> " if i == sel else "  ") + "%s %s" % (a, b), 0, 12 + i * 10)
    if modo == 2:
        oled.text("0-%d  barrido" % BARRIDO_MAX, 0, 54)
    else:
        oled.text("%d MHz" % (2400 + CANALES[idx_canal]), 0, 54)
    oled.show()


def cambiar():
    global modo, idx_canal, idx_rate
    estaba = activo
    if estaba:
        detener()
    if sel == 0:
        modo = (modo + 1) % 3
    elif sel == 1:
        idx_canal = (idx_canal + 1) % len(CANALES)
        radio.set_channel(CANALES[idx_canal])
    elif sel == 2:
        radio.set_power((radio.power + 1) % 4)
    else:
        idx_rate = (idx_rate + 1) % len(soportadas)
        set_rate(soportadas[idx_rate])
    if estaba:
        iniciar()
    show()


def barrido():
    global barrido_ch, t_ch
    radio.send(datos())
    if time.ticks_diff(time.ticks_ms(), t_ch) >= PASO_MS:
        barrido_ch = (barrido_ch + 1) % (BARRIDO_MAX + 1)
        radio.set_channel(barrido_ch)
        t_ch = time.ticks_ms()


oled.fill(0)
oled.text("Generador para", 0, 16)
oled.text("analizador de", 0, 28)
oled.text("espectros", 0, 40)
oled.show()
print("Espectro | canales:", CANALES, "| velocidades:", [RATES[r] for r in soportadas])
time.sleep(2)
show()

while True:
    if pressed(btn_sel):
        sel = (sel + 1) % 4
        show()
    if pressed(btn_chg):
        cambiar()
    if pressed(btn_go):
        if activo:
            detener()
        else:
            iniciar()
        show()

    if activo and modo_activo == 1:
        radio.send(datos())
    elif activo and modo_activo == 2:
        barrido()
    else:
        time.sleep_ms(10)
