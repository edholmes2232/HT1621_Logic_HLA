#   Benjamin DELPY `gentilkiwi`
#   https://blog.gentilkiwi.com / 
#   benjamin@gentilkiwi.com
#   Licence : https://creativecommons.org/licenses/by/4.0/
#
#   High Level Analyzer for NXP PN532 NFC chip on SPI bus
#   SPI settings:
#    - Significant Bit:   MSB
#    - Bits per Transfer: 1
#    - Clock State:       CPOL = 1
#    - Clock Phase:       CPHA = 1
#    - Enable Line:       Active Low

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame
from enum import Enum

class DECODER_STATE(Enum):
    START = 0
    GET_MODE = 1
    GET_ADDRESS = 2
    GET_DATA_NIBBLES = 3

HT1621_CMD = {
    0b110: "Read (0b110)",
    0b101: "Write (0b101)",
    0b100: "Command (0b100)",
}



class Hla(HighLevelAnalyzer):
    
    def __init__(self):
        self.state = DECODER_STATE.START
        self.mode_buffer = []
        self.address_buffer = []
        self.data_buffer = []
        self.nibble_list = []
        self.transaction_data = {}
        self.transaction_start_time = None
        self.transaction_end_time = None
        self.mode_type = None
        
    def decode(self, frame: AnalyzerFrame):
        if frame.type == 'enable':
            self.state = DECODER_STATE.GET_MODE
            self.mode_buffer = []
            self.address_buffer = []
            self.data_buffer = []
            self.nibble_list = []
            self.transaction_data = {}
            self.transaction_start_time = None
            self.transaction_end_time = None
            self.mode_type = None
            return None

        elif frame.type == 'result':
            if self.state == DECODER_STATE.GET_MODE:
                self.decode_mode(frame)
            elif self.state == DECODER_STATE.GET_ADDRESS:
                self.decode_address(frame)
            elif self.state == DECODER_STATE.GET_DATA_NIBBLES:
                self.decode_nibble(frame)
            return None

        elif frame.type == 'disable':
            # Only return a frame if we have a transaction
            if self.transaction_start_time is not None and self.transaction_end_time is not None and self.mode_type is not None:
                data_dict = {}
                if hasattr(self, 'address_value'):
                    data_dict['address'] = self.address_value
                for i, nibble in enumerate(self.nibble_list):
                    data_dict[f'data{i}'] = f"0x{nibble:x}"
                frame = AnalyzerFrame(self.mode_type, self.transaction_start_time, self.transaction_end_time, data_dict)
            else:
                frame = None
            self.state = DECODER_STATE.START
            return frame

    def decode_mode(self, frame: AnalyzerFrame):
        if len(self.mode_buffer) == 0:
            self.transaction_start_time = frame.start_time
        codeb = frame.data['mosi']
        code = codeb[0]
        self.mode_buffer.append(code)
        if len(self.mode_buffer) == 3:
            mode = self.mode_buffer[0] << 2 | self.mode_buffer[1] << 1 | self.mode_buffer[2]
            self.mode_type = HT1621_CMD.get(mode, f"Unknown Mode {mode}")
            self.state = DECODER_STATE.GET_ADDRESS
            self.address_buffer = []

    def decode_address(self, frame: AnalyzerFrame):
        if len(self.address_buffer) == 0:
            pass  # No need to set start time again
        codeb = frame.data['mosi']
        code = codeb[0]
        self.address_buffer.append(code)
        if len(self.address_buffer) == 6:
            address = (self.address_buffer[0] << 5 | self.address_buffer[1] << 4 |
                       self.address_buffer[2] << 3 | self.address_buffer[3] << 2 |
                       self.address_buffer[4] << 1 | self.address_buffer[5])
            self.address_value = f"0x{address:02x}"
            self.state = DECODER_STATE.GET_DATA_NIBBLES
            self.data_buffer = []

    def decode_nibble(self, frame: AnalyzerFrame):
        if len(self.data_buffer) == 0:
            pass  # No need to set start time again
        codeb = frame.data['mosi']
        code = codeb[0]
        self.data_buffer.append(code)
        if len(self.data_buffer) == 4:
            nibble = (self.data_buffer[0] << 3 | self.data_buffer[1] << 2 |
                      self.data_buffer[2] << 1 | self.data_buffer[3])
            self.nibble_list.append(nibble)
            self.data_buffer = []
            self.transaction_end_time = frame.end_time
