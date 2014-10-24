"""
Cryptographic Module for TPS File
"""

from construct import Array, GreedyRange, ULInt32


class TpsDecryptor:

    CHUNK_DATA_STRUCT = Array(16, ULInt32('data'))
    DATA_STRUCT = GreedyRange(CHUNK_DATA_STRUCT)

    def __init__(self, file, password, encoding='utf-8'):
        self.file = file
        self.encoding = encoding
        if password is None:
            self.password = password
        else:
            self.password = bytes(password, encoding=self.encoding) + b'\x00'
            self.keys = []

            byte_keys = [0] * 64

            for i in range(64):
                byte_keys[(i * 0x11) & 0x3F] = (i + self.password[(i + 1) % len(self.password)]) & 0xFF

            self.keys = self.CHUNK_DATA_STRUCT.parse(bytes(byte_keys))

            for i in range(2):
                for pos_a in range(16):
                    data_a = self.keys[pos_a]
                    pos_b = data_a & 0x0F
                    data_b = self.keys[pos_b]
                    self.keys[pos_b] = (data_a + (data_a & data_b)) & 0xFFFFFFFF
                    self.keys[pos_a] = ((data_a | data_b) + data_a) & 0xFFFFFFFF

    def decrypt(self, size, pos=None):
        if pos is None:
            pos = self.file.tell()
        align_start_pos = pos & 0xFFFFFFC0
        self.file.seek(align_start_pos)
        align_end_pos = ((size + pos - 1) | 0x3F) + 1
        result = self.DATA_STRUCT.parse(self.file.read(align_end_pos - align_start_pos))
        for chunk_number in range(len(result)):
            for i in range(16):
                pos_a = 15 - i
                key = self.keys[pos_a]
                pos_b = key & 0x0F

                data_a = result[chunk_number][pos_a]
                data_a = data_a - key

                data_b = result[chunk_number][pos_b]
                data_b = data_b - key

                result[chunk_number][pos_a] = ((data_a & key) | (data_b & ~key)) & 0xFFFFFFFF
                result[chunk_number][pos_b] = ((data_b & key) | (data_a & ~key)) & 0xFFFFFFFF

        self.file.seek(pos + size)
        return self.DATA_STRUCT.build(result)[pos - align_start_pos:pos - align_start_pos + size]

    def encrypt(self, size, pos=None):
        # TODO
        pass

    def is_encrypted(self):
        return self.password is not None
