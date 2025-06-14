# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame


# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):
    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'ht1621_frame': {
            'format': 'Type: {{data.type}}, Addr: {{data.addr}}, Data0: {{data.data0}}, Data1: {{data.data1}}, Data2: {{data.data2}}, Padding: {{data.padding}}'
        }
    }

    def __init__(self):
        '''
        Initialize HLA.

        Settings can be accessed using the same name used above.
        '''

        self.byte_buffer = []
        self.start_time = None

    def decode(self, frame: AnalyzerFrame):
        # Debug: print every frame's type and data
        print('DEBUG: frame.type =', frame.type, 'frame.data =', frame.data)
        # Try to find the correct key for the SPI byte
        byte_val = None
        for key in ['mosi', 'data', 'value', 'byte']:  # common keys
            if key in frame.data:
                byte_val = frame.data[key]
                break
        if byte_val is not None:
            # Convert single-byte bytes object to int if needed
            if isinstance(byte_val, bytes):
                byte_val = int.from_bytes(byte_val, 'big')
            if self.start_time is None:
                self.start_time = frame.start_time
            self.byte_buffer.append(byte_val)

        # When 8 bytes are collected, parse and output
        if len(self.byte_buffer) == 8:
            # Debug: print buffer contents and types
            print('DEBUG: byte_buffer =', self.byte_buffer, 'types:', [type(b) for b in self.byte_buffer])
            # Ensure all values are int and in 0-255
            if all(isinstance(b, int) and 0 <= b <= 255 for b in self.byte_buffer):
                raw = int.from_bytes(bytes(self.byte_buffer), 'big')
                type_val = (raw >> 61) & 0x7
                addr = (raw >> 55) & 0x3F
                data0 = (raw >> 39) & 0xFFFF
                data1 = (raw >> 23) & 0xFFFF
                data2 = (raw >> 7) & 0xFFFF
                padding = raw & 0x7F
                result = AnalyzerFrame(
                    'ht1621_frame',
                    self.start_time,
                    frame.end_time,
                    {
                        'type': type_val,
                        'addr': addr,
                        'data0': data0,
                        'data1': data1,
                        'data2': data2,
                        'padding': padding
                    }
                )
                self.byte_buffer = []
                self.start_time = None
                return result
            else:
                print('ERROR: Invalid byte_buffer contents:', self.byte_buffer)
                self.byte_buffer = []
                self.start_time = None
        return None
