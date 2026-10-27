# main_alcance_tx.py -> Pico 1 (TRANSMISOR) - prueba de alcance 4.2
# Necesita en la Pico: nrf24.py y ssd1306.py
# Botones: GP10 = velocidad, GP11 = potencia, GP12 = iniciar prueba
# La prueba manda N_PAQ paquetes y muestra cuántos confirmó el receptor (ACK).
from machine import Pin, SPI, I2C
import time
import ssd1306
from nrf24 import NRF24, RATES, POWER_DBM, RF_SETUP

# ---------- Configuración ----------
CHANNEL  = 76      # 2476 MHz: arriba de los canales Wi-Fi 1/6/11 (igual en el RX)
N_PAQ    = 100     # paquetes por prueba (máximo 255)
PAUSA_MS = 20      # pausa entre paquetes

# ---------- Hardware ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
radio = NRF24(spi, csn=17, ce=20, channel=CHANNEL, power=3, rate=1, auto_ack=True)

btn_rate = Pin(10, Pin.IN, Pin.PULL_UP)
btn_pwr  = Pin(11, Pin.IN, Pin.PULL_UP)
btn_go   = Pin(12, Pin.IN, Pin.PULL_UP)
led_ok   = Pin(21, Pin.OUT)
led_err  = Pin(22, Pin.OUT)


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


# Detecta si el módulo soporta 250 kbps (solo los NRF24L01+)
soportadas = [1, 2]
set_rate(0)
if radio.read_reg(RF_SETUP)[0] & 0x20:
    soportadas = [0, 1, 2]
set_rate(1)
idx_rate = soportadas.index(1)

res = ("", "", "")   # líneas del último resultado


def show(estado):
    oled.fill(0)
    oled.text("ALCANCE TX c%d" % radio.channel, 0, 0)
    oled.text("%s %d dBm" % (RATES[radio.rate], POWER_DBM[radio.power]), 0, 12)
    oled.text(res[0], 0, 26)
    oled.text(res[1], 0, 36)
    oled.text(res[2], 0, 46)
    oled.text(estado, 0, 56)
    oled.show()


def prueba():
    global res
    ok = primera = reint = 0
    show("Probando...")
    for i in range(N_PAQ):
        pkt = bytes([i, N_PAQ]) + bytes(30)
        exito = radio.send(pkt)
        arc = radio.read_reg(0x08)[0] & 0x0F      # OBSERVE_TX: reintentos
        reint += arc
        if exito:
            ok += 1
            if arc == 0:
                primera += 1
        time.sleep_ms(PAUSA_MS)
    res = ("OK %d/%d" % (ok, N_PAQ),
           "1er int: %d" % primera,
           "Reint: %d" % reint)
    print("%s | %d dBm | OK %d/%d | 1er intento %d | reintentos %d" %
          (RATES[radio.rate], POWER_DBM[radio.power], ok, N_PAQ, primera, reint))
    led = led_ok if ok >= 0.9 * N_PAQ else led_err
    led.on()
    time.sleep_ms(500)
    led.off()
    show("Listo")


# ---------- Inicio ----------
oled.fill(0)
oled.text("Prueba de alcance", 0, 16)
oled.text("Transmisor", 0, 32)
oled.show()
print("Alcance TX | canal", radio.channel, "| velocidades:", [RATES[r] for r in soportadas])
time.sleep(2)
show("Listo")

while True:
    if pressed(btn_rate):
        idx_rate = (idx_rate + 1) % len(soportadas)
        set_rate(soportadas[idx_rate])
        show("Velocidad cambio")
    if pressed(btn_pwr):
        radio.set_power((radio.power + 1) % 4)
        show("Potencia cambio")
    if pressed(btn_go):
        prueba()
    time.sleep_ms(10)
