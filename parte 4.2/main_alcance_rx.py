# main_alcance_rx.py -> Pico 2 (RECEPTOR) - prueba de alcance 4.2
# Necesita en la Pico: nrf24.py y ssd1306.py
# Botones: GP10 = velocidad, GP11 = potencia (deben coincidir con el TX)
# Cuenta cuántos paquetes de la prueba del transmisor le llegan.
from machine import Pin, SPI, I2C
import time
import ssd1306
from nrf24 import NRF24, RATES, POWER_DBM, RF_SETUP

# ---------- Configuración ----------
CHANNEL = 76       # igual que el transmisor

# ---------- Hardware ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
radio = NRF24(spi, csn=17, ce=20, channel=CHANNEL, power=3, rate=1, auto_ack=True)

btn_rate = Pin(10, Pin.IN, Pin.PULL_UP)
btn_pwr  = Pin(11, Pin.IN, Pin.PULL_UP)
led_ok   = Pin(21, Pin.OUT)


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

count = 0          # paquetes recibidos en la prueba actual
total = 0          # paquetes que manda el transmisor
last_seq = 0
done = True        # la prueba anterior ya terminó
t_last = time.ticks_ms()


def show(linea1, linea2):
    oled.fill(0)
    oled.text("ALCANCE RX c%d" % radio.channel, 0, 0)
    oled.text("%s %d dBm" % (RATES[radio.rate], POWER_DBM[radio.power]), 0, 12)
    oled.text(linea1, 0, 30)
    oled.text(linea2, 0, 44)
    oled.show()


def reiniciar_escucha():
    radio.stop_listening()
    radio.start_listening()


oled.fill(0)
oled.text("Prueba de alcance", 0, 16)
oled.text("Receptor", 0, 32)
oled.show()
print("Alcance RX | canal", radio.channel, "| velocidades:", [RATES[r] for r in soportadas])
time.sleep(2)
radio.start_listening()
show("Esperando...", "")

while True:
    if pressed(btn_rate):
        idx_rate = (idx_rate + 1) % len(soportadas)
        radio.stop_listening()
        set_rate(soportadas[idx_rate])
        radio.start_listening()
        show("Velocidad cambio", "")

    if pressed(btn_pwr):
        radio.stop_listening()
        radio.set_power((radio.power + 1) % 4)
        radio.start_listening()
        show("Potencia cambio", "")

    if radio.any():
        pkt = radio.recv()
        seq, total = pkt[0], pkt[1]
        if done or seq < last_seq:      # empieza una prueba nueva
            count = 0
            done = False
        last_seq = seq
        count += 1
        t_last = time.ticks_ms()
        led_ok.toggle()
        if seq == total - 1:            # llegó el último paquete
            done = True
            print("Prueba terminada: %d/%d | %s | %d dBm" %
                  (count, total, RATES[radio.rate], POWER_DBM[radio.power]))
            show("Rx %d de %d" % (count, total), "FIN")
        elif count % 25 == 0:
            show("Rx %d de %d" % (count, total), "Recibiendo...")

    # Si se perdió el último paquete, cierra la prueba por tiempo
    if not done and time.ticks_diff(time.ticks_ms(), t_last) > 1500:
        done = True
        print("Prueba terminada (tiempo): %d/%d" % (count, total))
        show("Rx %d de %d" % (count, total), "FIN")

    time.sleep_ms(2)
