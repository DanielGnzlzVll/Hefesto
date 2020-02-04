import serial
import socket


class BaseDriver:
    def __init__(self, *args, **kargs):
        self._open = False
        self.kargs = kargs
        self.init()
        self._open = True

    def __enter__(self):
        try:
            if not self._open:
                self.init()
        except:  # noqa
            pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
            self._open = False
        except:  # noqa
            pass

    def __del__(self):
        try:
            self.close()
            self._open = False
        except:  # noqa
            pass

    def close(self, *args, **kargs):
        self.conn.close()

    def init(self, *args, **kargs):
        pass

    def read(self, response_length, *args, **kargs):
        pass

    def wrie(self, data, *args, **kargs):
        pass

    def request(self, data, response_length, *args, **kargs):
        self.write(data, *args, **kargs)
        return self.read(response_length, *args, **kargs)


class SerialDriver(BaseDriver):
    def init(self, *args, **kargs):
        parity = getattr(serial, self.kargs.get("paridad"))
        stopbits = getattr(serial, self.kargs.get("bit_parada"))
        bytesize = getattr(serial, self.kargs.get("numero_bytes"))
        self.conn = serial.Serial(
            self.kargs.get("puerto_serial"),
            baudrate=self.kargs.get("baudrate"),
            bytesize=bytesize,
            stopbits=stopbits,
            parity=parity,
        )
        self.conn.timeout = self.kargs.get("tiempo_espera")
        self.conn.close()
        self.conn.open()
        self.conn.flushInput()

    def read(self, response_length, *args, **kargs):
        return self.conn.read(response_length)

    def write(self, data, *args, **kargs):
        try:
            self.conn.open()
            self.conn.flushInput()
        except:  # noqa
            pass
        self.conn.write(data)
        self.conn.flush()


class TPCDriver(BaseDriver):
    def init(self, *args, **kargs):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.kargs.get("ip"), self.kargs.get("puerto_tcp")))
        self.conn.settimeout(self.kargs.get("tiempo_espera"))

    def read(self, response_length, *args, **kargs):
        try:
            respuesta = self.conn.recv(response_length)
            return respuesta
        except socket.timeout:
            pass
        return b""

    def write(self, data, *args, **kargs):
        self.conn.settimeout(0.05)
        try:
            self.conn.recv(4096)
        except socket.timeout:
            pass
        self.conn.settimeout(self.kargs.get("tiempo_espera"))
        self.conn.send(data)
