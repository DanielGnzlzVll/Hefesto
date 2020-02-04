from serial.tools import list_ports


class ports:
    """
    iterable que sirve para listar los puertos seriales
    """

    def __init__(self, initial=None):
        self.initial = initial

    def __iter__(self):
        self.usb_i = 0
        usbs = list(list_ports.grep('usb'))
        self.usb_ports = usbs
        return self

    def __next__(self):
        if self.initial and self.usb_i == 0:
            r = self.initial
            self.initial = None
            return (r, r)
        try:
            port = self.usb_ports[self.usb_i]
            self.usb_i += 1
            return (port[0], str(port[1]))
        except:  # noqa
            raise StopIteration


def parce_dev_list(dispositivos):
    '''
    retorna la lista de dispositivos para la colsulta
    ej: "1-3, 5" -> [1, 2, 3, 5]

    :return: lista de dispositivos
    :rtype: list
    '''

    devs = []
    for part in dispositivos.split(', '):
        if '-' in part:
            a,  b = part.split('-')
            a,  b = int(a),  int(b)
            devs.extend(range(a,  b + 1))
        else:
            a = int(part)
            devs.append(a)
    return devs


def crc16(data: bytes):
    '''
    CRC-16-ModBus Algorithm.
    '''
    data = bytearray(data)
    poly = 0xA001
    crc = 0xFFFF
    for b in data:
        crc ^= (0xFF & b)
        for _ in range(0,  8):
            if (crc & 0x0001):
                crc = ((crc >> 1) & 0xFFFF) ^ poly
            else:
                crc = ((crc >> 1) & 0xFFFF)

    crc = crc & 0xFFFF
    crc = ((crc >> 8) & 0xFF) | ((crc << 8) & 0xFF00)
    return crc
