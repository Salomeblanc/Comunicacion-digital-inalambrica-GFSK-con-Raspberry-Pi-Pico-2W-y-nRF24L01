# main_ber_tx.py -> Pico 1 (TRANSMISOR) - prueba de BER 4.3
# Archivos en la Pico: nrf24.py, ssd1306.py, alfabetos.txt, aleatorio.txt
# Botones: GP10 = velocidad, GP11 = potencia, GP12 = enviar los dos archivos
# Sin ACK y sin CRC: el receptor recibe los paquetes aunque tengan bits erróneos
# y los compara con su copia del archivo para contar los errores.
from machine import Pin, SPI, I2C
import time
import ssd1306
from nrf24 import NRF24, RATES, POWER_DBM, RF_SETUP

# ---------- Configuración (igual en el RX) ----------
CHANNEL  = 76
REPEATS  = 3        # veces que se manda cada archivo (máximo 300)
PAUSA_MS = 5        # pausa entre paquetes
DATA     = 28       # bytes de archivo por paquete (4 bytes de cabecera)
FILES    = ("alfabetos.txt", "aleatorio.txt")

# ---------- Hardware ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
radio = NRF24(spi, csn=17, ce=20, channel=CHANNEL, power=3, rate=1,
              auto_ack=False, crc=False)

btn_rate = Pin(10, Pin.IN, Pin.PULL_UP)
btn_pwr  = Pin(11, Pin.IN, Pin.PULL_UP)
btn_go   = Pin(12, Pin.IN, Pin.PULL_UP)
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

archivos = []
for nombre in FILES:
    with open(nombre, "rb") as f:
        archivos.append(f.read())


def total_pk(fid):
    return (len(archivos[fid]) // DATA) * REPEATS


def show(estado):
    oled.fill(0)
    oled.text("BER TX c%d" % radio.channel, 0, 0)
    oled.text("%s %d dBm" % (RATES[radio.rate], POWER_DBM[radio.power]), 0, 12)
    oled.text("%d paq/archivo" % total_pk(0), 0, 30)
    oled.text(estado, 0, 48)
    oled.show()


def enviar_archivo(fid):
    d = archivos[fid]
    n_pk = len(d) // DATA
    for seq in range(n_pk * REPEATS):
        i = seq % n_pk
        h = bytes([fid, seq >> 8, seq & 0xFF])
        cab = h + bytes([h[0] ^ h[1] ^ h[2] ^ 0xA5])    # cabecera + checksum
        radio.send(cab + d[i * DATA:(i + 1) * DATA])
        time.sleep_ms(PAUSA_MS)


oled.fill(0)
oled.text("Prueba de BER", 0, 16)
oled.text("Transmisor", 0, 32)
oled.show()
print("BER TX | canal", radio.channel, "| velocidades:", [RATES[r] for r in soportadas],
      "| paquetes por archivo:", total_pk(0))
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
        for fid in (0, 1):
            show("Enviando %s" % ("ALF", "ALE")[fid])
            enviar_archivo(fid)
            time.sleep_ms(300)
        led_ok.on()
        time.sleep_ms(300)
        led_ok.off()
        print("Envio terminado | %s | %d dBm" %
              (RATES[radio.rate], POWER_DBM[radio.power]))
        show("Envio terminado")
    time.sleep_ms(10)
