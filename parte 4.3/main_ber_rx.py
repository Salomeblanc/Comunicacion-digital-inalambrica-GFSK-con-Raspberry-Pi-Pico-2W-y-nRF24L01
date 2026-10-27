# main_ber_rx.py -> Pico 2 (RECEPTOR) - prueba de BER 4.3
# Archivos en la Pico: nrf24.py, ssd1306.py, alfabetos.txt, aleatorio.txt
# Botones: GP10 = velocidad, GP11 = potencia (deben coincidir con el TX)
# Compara cada paquete con su copia del archivo y cuenta los bits erróneos.
from machine import Pin, SPI, I2C
import time
import ssd1306
from nrf24 import NRF24, RATES, POWER_DBM, RF_SETUP

# ---------- Configuración (igual en el TX) ----------
CHANNEL = 76
REPEATS = 3
DATA    = 28
FILES   = ("alfabetos.txt", "aleatorio.txt")
TAG     = ("ALF", "ALE")

# ---------- Hardware ----------
i2c  = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
spi  = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
           sck=Pin(18), mosi=Pin(19), miso=Pin(16))
radio = NRF24(spi, csn=17, ce=20, channel=CHANNEL, power=3, rate=1,
              auto_ack=False, crc=False)

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

archivos = []
for nombre in FILES:
    with open(nombre, "rb") as f:
        archivos.append(f.read())

POP = bytes(bin(i).count("1") for i in range(256))   # bits en 1 de cada byte

# Estadísticas por archivo: [recibidos, cabeceras malas, bits erróneos, paquetes con error]
st = [[0, 0, 0, 0], [0, 0, 0, 0]]
done = [True, True]
last_seq = [0, 0]
cur = None            # archivo que se está recibiendo
t_last = time.ticks_ms()
lineas = [("", ""), ("", "")]


def total_pk(fid):
    return (len(archivos[fid]) // DATA) * REPEATS


def reiniciar(fid):
    st[fid] = [0, 0, 0, 0]
    done[fid] = False
    last_seq[fid] = 0
    lineas[fid] = ("", "")


def show():
    oled.fill(0)
    oled.text("BER RX c%d" % radio.channel, 0, 0)
    oled.text("%s %d dBm" % (RATES[radio.rate], POWER_DBM[radio.power]), 0, 10)
    y = 24
    for fid in (0, 1):
        oled.text(lineas[fid][0], 0, y)
        oled.text(lineas[fid][1], 0, y + 10)
        y += 22
    oled.show()


def finalizar(fid):
    done[fid] = True
    rx, hb, be, pe = st[fid]
    tot = total_pk(fid)
    bits = rx * DATA * 8
    perd = tot - rx - hb
    if bits:
        ber = be / bits
        ber_txt = "0" if be == 0 else "%.2e" % ber
    else:
        ber_txt = "sin datos"
    print("%s | %s | %d dBm | recibidos %d/%d | cabeceras malas %d | perdidos %d | "
          "bits erroneos %d de %d | BER %s | paquetes con error %d" %
          (TAG[fid], RATES[radio.rate], POWER_DBM[radio.power], rx, tot, hb, perd,
           be, bits, ber_txt, pe))
    lineas[fid] = ("%s %d/%d" % (TAG[fid], rx, tot),
                   "e=%d %s" % (be, "BER 0" if (bits and be == 0) else
                                ("%.1e" % (be / bits) if bits else "-")))
    show()


def procesar(pkt):
    """Devuelve el archivo al que pertenece el paquete (o None si la cabecera falla)."""
    global cur
    fid = pkt[0]
    if fid > 1 or pkt[3] != (pkt[0] ^ pkt[1] ^ pkt[2] ^ 0xA5):
        if cur is not None and not done[cur]:
            st[cur][1] += 1
        return None
    seq = (pkt[1] << 8) | pkt[2]
    if cur is not None and cur != fid and not done[cur]:
        finalizar(cur)
    if done[fid] or seq < last_seq[fid]:
        reiniciar(fid)
    cur = fid
    last_seq[fid] = seq
    d = archivos[fid]
    n_pk = len(d) // DATA
    i = seq % n_pk
    esperado = d[i * DATA:(i + 1) * DATA]
    recibido = pkt[4:4 + DATA]
    e = 0
    for a, b in zip(recibido, esperado):
        if a != b:
            e += POP[a ^ b]
    s = st[fid]
    s[0] += 1
    if e:
        s[2] += e
        s[3] += 1
    return fid


oled.fill(0)
oled.text("Prueba de BER", 0, 16)
oled.text("Receptor", 0, 32)
oled.show()
print("BER RX | canal", radio.channel, "| velocidades:", [RATES[r] for r in soportadas])
time.sleep(2)
radio.start_listening()
lineas[0] = ("Esperando...", "")
show()

while True:
    if pressed(btn_rate):
        idx_rate = (idx_rate + 1) % len(soportadas)
        radio.stop_listening()
        set_rate(soportadas[idx_rate])
        radio.start_listening()
        show()
    if pressed(btn_pwr):
        radio.stop_listening()
        radio.set_power((radio.power + 1) % 4)
        radio.start_listening()
        show()

    if radio.any():
        pkt = radio.recv()
        t_last = time.ticks_ms()
        fid = procesar(pkt)
        if fid is not None and last_seq[fid] == total_pk(fid) - 1:
            finalizar(fid)
            led_ok.toggle()

    # Si se perdió el último paquete, cierra el archivo por tiempo
    if cur is not None and not done[cur] and time.ticks_diff(time.ticks_ms(), t_last) > 1500:
        finalizar(cur)

    time.sleep_ms(1)
