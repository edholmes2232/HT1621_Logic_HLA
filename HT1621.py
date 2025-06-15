#   Ed Holmes
#   edholmes(at)gmail.com
#   Licence : https://creativecommons.org/licenses/by/4.0/
#
#   Developed using HT1621 datasheet v3.40
#
#   High Level Analyzer for HT1621 LCD Driver on SPI bus
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
    GET_COMMAND = 4

HT1621_MODE = {
    0b110: "Read (0b110)",
    0b101: "Write (0b101)",
    0b100: "Command (0b100)",
}

HT1621_COMMAND = [
    # SYS DIS      0000-0000-X
    {"name": "SYS DIS",    "value": 0b000000000, "mask": 0b111111110},
    # SYS EN       0000-0001-X
    {"name": "SYS EN",     "value": 0b000000010, "mask": 0b111111110},
    # LCD OFF      0000-0010-X
    {"name": "LCD OFF",    "value": 0b000000100, "mask": 0b111111110},
    # LCD ON       0000-0011-X
    {"name": "LCD ON",     "value": 0b000000110, "mask": 0b111111110},
    # TIMER DIS    0000-0100-X
    {"name": "TIMER DIS",  "value": 0b000001000, "mask": 0b111111110},
    # WDT DIS      0000-0101-X
    {"name": "WDT DIS",    "value": 0b000001010, "mask": 0b111111110},
    # TIMER EN     0000-0110-X
    {"name": "TIMER EN",   "value": 0b000001100, "mask": 0b111111110},
    # WDT EN       0000-0111-X
    {"name": "WDT EN",     "value": 0b000001110, "mask": 0b111111110},
    # TONE OFF     0000-1000-X
    {"name": "TONE OFF",   "value": 0b000010000, "mask": 0b111111110},
    # TONE ON      0000-1001-X
    {"name": "TONE ON",    "value": 0b000010010, "mask": 0b111111110},
    # CLR TIMER    0000-11XX-X
    {"name": "CLR TIMER",  "value": 0b000011000, "mask": 0b111111000},
    # CLR WDT      0000-111X-X
    {"name": "CLR WDT",    "value": 0b000011100, "mask": 0b111111100},
    # XTAL 32K     0001-01XX-X
    {"name": "XTAL 32K",   "value": 0b000101000, "mask": 0b111111000},
    # RC 256K      0001-10XX-X
    {"name": "RC 256K",    "value": 0b000110000, "mask": 0b111111000},
    # EXT 256K     0001-11XX-X
    {"name": "EXT 256K",   "value": 0b000111000, "mask": 0b111111000},
    # BIAS 1/2     0010-abX0-X
    {"name": "BIAS 1/2",   "value": 0b001000000, "mask": 0b111100010},
    # BIAS 1/3     0010-abX1-X
    {"name": "BIAS 1/3",   "value": 0b001000010, "mask": 0b111100010},
    # TONE 4K      010X-XXXX-X
    {"name": "TONE 4K",    "value": 0b010000000, "mask": 0b111000000},
    # TONE 2K      011X-XXXX-X
    {"name": "TONE 2K",    "value": 0b011000000, "mask": 0b111000000},
    # IRQ DIS      100X-0XXX-X
    {"name": "IRQ DIS",    "value": 0b100000000, "mask": 0b111010000},
    # IRQ EN       100X-1XXX-X
    {"name": "IRQ EN",     "value": 0b100010000, "mask": 0b111010000},
    # F1           101X-X000-X
    {"name": "F1",         "value": 0b101000000, "mask": 0b111001110},
    # F2           101X-X001-X
    {"name": "F2",         "value": 0b101000010, "mask": 0b111001110},
    # F4           101X-X010-X
    {"name": "F4",         "value": 0b101000100, "mask": 0b111001110},
    # F8           101X-X011-X
    {"name": "F8",         "value": 0b101000110, "mask": 0b111001110},
    # F16          101X-X100-X
    {"name": "F16",        "value": 0b101001000, "mask": 0b111001110},
    # F32          101X-X101-X
    {"name": "F32",        "value": 0b101001010, "mask": 0b111001110},
    # F64          101X-X110-X
    {"name": "F64",        "value": 0b101001100, "mask": 0b111001110},
    # F128         101X-X111-X
    {"name": "F128",       "value": 0b101001110, "mask": 0b111001110},
    # TEST         1110-0000-X
    {"name": "TEST",       "value": 0b111000000, "mask": 0b111111110},
    # NORMAL       1110-0011-X
    {"name": "NORMAL",     "value": 0b111000110, "mask": 0b111111110},
]

def lookup_command(bits):
    for cmd in HT1621_COMMAND:
        if (bits & cmd["mask"]) == (cmd["value"] & cmd["mask"]):
            return cmd["name"]
    return None

class Hla(HighLevelAnalyzer):
    
    def __init__(self):
        self.state = DECODER_STATE.START
        self.mode_buffer = []
        self.address_buffer = []
        self.data_buffer = []
        self.nibble_list = []
        self.command_buffer = []
        self.transaction_start_time = None
        self.transaction_end_time = None
        self.mode_type = None
        self.command_value = None
        self.command_bits = None
        
    def decode(self, frame: AnalyzerFrame):
        if frame.type == 'enable':
            self.state = DECODER_STATE.GET_MODE
            self.mode_buffer = []
            self.address_buffer = []
            self.data_buffer = []
            self.nibble_list = []
            self.command_buffer = []
            self.transaction_start_time = None
            self.transaction_end_time = None
            self.mode_type = None
            self.command_value = None
            self.command_bits = None
            return None

        elif frame.type == 'result':
            if self.state == DECODER_STATE.GET_MODE:
                self.decode_mode(frame)
            elif self.state == DECODER_STATE.GET_ADDRESS:
                self.decode_address(frame)
            elif self.state == DECODER_STATE.GET_DATA_NIBBLES:
                self.decode_nibble(frame)
            elif self.state == DECODER_STATE.GET_COMMAND:
                self.decode_command(frame)
            return None

        elif frame.type == 'disable':
            if self.transaction_start_time is not None and self.transaction_end_time is not None and self.mode_type is not None:
                data_dict = {}
                if self.mode_type == 'Command (0b100)':
                    data_dict['command'] = self.command_value if self.command_value else 'Unknown Command'
                    data_dict['command_bits'] = f"0b{self.command_bits:09b}" if self.command_bits is not None else None
                else:
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
            self.mode_type = HT1621_MODE.get(mode, f"Unknown Mode {mode}")
            if mode == 0b100:
                self.state = DECODER_STATE.GET_COMMAND
                self.command_buffer = []
            else:
                self.state = DECODER_STATE.GET_ADDRESS
                self.address_buffer = []

    def decode_address(self, frame: AnalyzerFrame):
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
        codeb = frame.data['mosi']
        code = codeb[0]
        self.data_buffer.append(code)
        if len(self.data_buffer) == 4:
            nibble = (self.data_buffer[0] << 3 | self.data_buffer[1] << 2 |
                      self.data_buffer[2] << 1 | self.data_buffer[3])
            self.nibble_list.append(nibble)
            self.data_buffer = []
            self.transaction_end_time = frame.end_time

    def decode_command(self, frame: AnalyzerFrame):
        codeb = frame.data['mosi']
        code = codeb[0]
        self.command_buffer.append(code)
        if len(self.command_buffer) == 9:
            bits = 0
            for i, bit in enumerate(self.command_buffer):
                bits |= (bit << (8 - i))
            self.command_bits = bits
            self.command_value = lookup_command(bits)
            self.transaction_end_time = frame.end_time
