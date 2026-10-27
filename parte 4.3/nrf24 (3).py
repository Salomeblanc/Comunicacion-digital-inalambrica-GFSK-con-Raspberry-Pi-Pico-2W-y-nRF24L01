# nrf24.py - Driver mínimo del NRF24L01 para Raspberry Pi Pico (MicroPython)
# Copiar este archivo a las DOS Pico.
import time
from machine import Pin

# ---------- Comandos SPI ----------
R_REGISTER   = 0x00   # 0x00 | dirección
W_REGISTER   = 0x20   # 0x20 | dirección  (RF_CH -> 0x25)
R_RX_PAYLOAD = 0x61
W_TX_PAYLOAD = 0xA0
FLUSH_TX     = 0xE1
FLUSH_RX     = 0xE2
NOP          = 0xFF

# ---------- Registros ----------
CONFIG      = 0x00
EN_AA       = 0x01
EN_RXADDR   = 0x02
SETUP_AW    = 0x03
SETUP_RETR  = 0x04
RF_CH       = 0x05
RF_SETUP    = 0x06
STATUS      = 0x07
RX_ADDR_P0  = 0x0A
TX_ADDR     = 0x10
RX_PW_P0    = 0x11
FIFO_STATUS = 0x17

PAYLOAD   = 32                      # payload fijo de 32 bytes
ADDRESS   = b"UMNG1"                # misma dirección en TX y RX
POWER_DBM = (-18, -12, -6, 0)       # índice 0..3 -> bits RF_PWR
RATES     = ("250 kbps", "1 Mbps", "2 Mbps")
_RATE_BITS = (0x20, 0x00, 0x08)     # RF_DR_LOW / RF_DR_HIGH
_CFG = 0x0E                         # EN_CRC + CRC de 2 bytes + PWR_UP


class NRF24:
    def __init__(self, spi, csn, ce, channel=40, power=3, rate=1, auto_ack=True, crc=True):
        self.spi = spi
        self.csn = Pin(csn, Pin.OUT, value=1)
        self.ce = Pin(ce, Pin.OUT, value=0)
        self.channel = channel
        self.power = power
        self.rate = rate
        # crc=False solo funciona con auto_ack=False (prueba de BER)
        self._cfg = _CFG if crc else 0x02        # 0x02 = solo PWR_UP, sin CRC

        time.sleep_ms(100)                       # arranque del módulo
        self.write_reg(CONFIG, self._cfg)        # PWR_UP, modo TX (standby-I)
        time.sleep_ms(5)
        self.write_reg(SETUP_AW, 0x03)           # dirección de 5 bytes
        self.write_reg(SETUP_RETR, 0x5F)         # 1500 us, 15 reintentos
        self.write_reg(EN_AA, 0x01 if auto_ack else 0x00)
        self.write_reg(EN_RXADDR, 0x01)          # solo pipe 0
        self.write_reg(RX_ADDR_P0, ADDRESS)
        self.write_reg(TX_ADDR, ADDRESS)
        self.write_reg(RX_PW_P0, PAYLOAD)
        self.write_reg(RF_CH, channel)
        self._write_rf_setup()
        self._cmd(FLUSH_TX)
        self._cmd(FLUSH_RX)
        self.write_reg(STATUS, 0x70)             # limpiar banderas

    # ---------- SPI de bajo nivel ----------
    def _cmd(self, cmd, data=b"", n=0):
        """Una transacción SPI: CSN=0, comando, datos, CSN=1.
        Devuelve (STATUS, bytes leídos)."""
        out = bytearray([cmd]) + bytearray(data) + bytearray(n)
        inp = bytearray(len(out))
        self.csn.value(0)
        self.spi.write_readinto(out, inp)
        self.csn.value(1)
        return inp[0], inp[1:]

    def read_reg(self, reg, n=1):
        return self._cmd(R_REGISTER | reg, n=n)[1]

    def write_reg(self, reg, val):
        if isinstance(val, int):
            val = bytes([val])
        self._cmd(W_REGISTER | reg, val)

    # ---------- Configuración ----------
    def _write_rf_setup(self):
        self.write_reg(RF_SETUP, _RATE_BITS[self.rate] | (self.power << 1))

    def set_channel(self, ch):
        """Escribe RF_CH (W_REGISTER 0x25) y lo lee de vuelta (R_REGISTER 0x05)."""
        self.channel = ch
        self.write_reg(RF_CH, ch)
        return self.read_reg(RF_CH)[0]

    def set_power(self, p):
        self.power = p
        self._write_rf_setup()
        return self.read_reg(RF_SETUP)[0]

    @property
    def freq_mhz(self):
        return 2400 + self.channel

    # ---------- Transmisión ----------
    def send(self, payload):
        """Envía un paquete (<=32 bytes). True si se transmitió/confirmó."""
        payload = bytes(payload) + bytes(PAYLOAD - len(payload))
        self._cmd(W_TX_PAYLOAD, payload)         # carga el paquete en el FIFO
        self.ce.value(1)                         # pulso CE > 10 us inicia TX
        time.sleep_us(20)
        self.ce.value(0)

        st = 0
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 200:
            st = self._cmd(NOP)[0]               # NOP devuelve STATUS
            if st & 0x30:                        # TX_DS (0x20) o MAX_RT (0x10)
                break
        self.write_reg(STATUS, 0x70)             # limpiar banderas
        if st & 0x10:                            # se agotaron los reintentos
            self._cmd(FLUSH_TX)
            return False
        return bool(st & 0x20)

    # ---------- Recepción ----------
    def start_listening(self):
        self.write_reg(CONFIG, self._cfg | 0x01) # PRIM_RX = 1
        self.write_reg(STATUS, 0x70)
        self._cmd(FLUSH_RX)
        self.ce.value(1)
        time.sleep_us(150)

    def stop_listening(self):
        self.ce.value(0)
        self.write_reg(CONFIG, self._cfg)        # PRIM_RX = 0

    def any(self):
        return not (self.read_reg(FIFO_STATUS)[0] & 0x01)   # RX_EMPTY

    def recv(self):
        data = self._cmd(R_RX_PAYLOAD, n=PAYLOAD)[1]
        self.write_reg(STATUS, 0x40)             # limpiar RX_DR
        return bytes(data)
