from construct import Byte, Bytes, Embed, Enum, IfThenElse, Peek, String, Struct, Switch, UBInt32, ULInt16, ULInt32

from .tpspage import PAGE_HEADER_STRUCT
from .utils import check_value

record_encoding = None

RECORD_TYPE = Enum(Byte('type'),
                   NULL=None,
                   DATA=0xF3,
                   METADATA=0xF6,
                   TABLE_DEFINITION=0xFA,
                   TABLE_NAME=0xFE,
                   _default_='INDEX', )

DATA_RECORD_DATA = Struct('field_data',
                          UBInt32('record_number'),
                          Bytes('data', lambda ctx: ctx['data_size'] - 9))

METADATA_RECORD_DATA = Struct('field_metadata',
                              Byte('metadata_type'),
                              ULInt32('metadata_record_count'),
                              ULInt32('metadata_record_last_access'))

TABLE_DEFINITION_RECORD_DATA = Struct('table_definition',
                                      Bytes('table_definition_bytes', lambda ctx: ctx['data_size'] - 5))

INDEX_RECORD_DATA = Struct('field_index',
                           Bytes('data', lambda ctx: ctx['data_size'] - 10),
                           ULInt32('record_number'))

RECORD_STRUCT = Struct('record',
                       ULInt16('data_size'),
                       Peek(Byte('first_byte')),
                       Embed(IfThenElse('record_type', lambda ctx: ctx['first_byte'] == 0xFE,
                                        Embed(Struct('record',
                                                     RECORD_TYPE,
                                                     String('table_name', lambda ctx: ctx['data_size'] - 5,
                                                            encoding=record_encoding),
                                                     UBInt32('table_number'), )),
                                        Embed(Struct('record',
                                                     UBInt32('table_number'),
                                                     RECORD_TYPE,
                                                     Switch('record_type',
                                                            lambda ctx: ctx.type,
                                                            {
                                                                'DATA': Embed(DATA_RECORD_DATA),
                                                                'METADATA': Embed(METADATA_RECORD_DATA),
                                                                'TABLE_DEFINITION': Embed(
                                                                    TABLE_DEFINITION_RECORD_DATA),
                                                                'INDEX': Embed(INDEX_RECORD_DATA)
                                                            }))))))


class TpsRecord:
    def __init__(self, header_size, data):
        self.header_size = header_size
        self.data_bytes = data
        # print(data)

        data_size = len(self.data_bytes) - 2

        # print('data_size', data_size, header_size)

        if data_size == 0:
            self.type = 'NULL'
        else:
            self.data = RECORD_STRUCT.parse(self.data_bytes)
            self.type = self.data.type


class TpsRecordsList:
    def __init__(self, tps, tps_page, encoding=None, check=False):
        self.tps = tps
        self.check = check
        self.tps_page = tps_page
        self.encoding = encoding
        global record_encoding
        record_encoding = encoding
        self.__records = []

        if self.tps_page.hierarchy_level == 0:
            if self.tps_page.ref in self.tps.cache_pages:
                self.__records = tps.cache_pages[self.tps_page.ref]
            else:
                data = self.tps.read(self.tps_page.size - PAGE_HEADER_STRUCT.sizeof(),
                                     self.tps_page.ref * 0x100 + self.tps.header.size + PAGE_HEADER_STRUCT.sizeof())

                if self.tps_page.uncompressed_size > self.tps_page.size:
                    data = self.__uncompress(data)

                    if self.check:
                        check_value('record_data.size', len(data) + PAGE_HEADER_STRUCT.sizeof(),
                                    tps_page.uncompressed_size)

                record_data = b''
                pos = 0
                record_size = 0
                record_header_size = 0

                while pos < len(data):
                    byte_counter = data[pos]
                    pos += 1
                    if (byte_counter & 0x80) == 0x80:
                        record_size = data[pos + 1] * 0x100 + data[pos]
                        pos += 2
                    if (byte_counter & 0x40) == 0x40:
                        record_header_size = data[pos + 1] * 0x100 + data[pos]
                        pos += 2
                    byte_counter &= 0x3F
                    new_data_size = record_size - byte_counter
                    record_data = record_data[:byte_counter] + data[pos:pos + new_data_size]
                    self.__records.append(TpsRecord(record_header_size, ULInt16('data_size').build(record_size)
                                                    + record_data))
                    pos += new_data_size

                if self.tps.cached and self.tps_page.ref not in tps.cache_pages:
                    tps.cache_pages[self.tps_page.ref] = self.__records

    def __uncompress(self, data):
        pos = 0
        result = b''
        while pos < len(data):
            repeat_rel_offset = data[pos]
            pos += 1

            if repeat_rel_offset > 0x7F:
                # size repeat_count = 2 bytes
                repeat_rel_offset = ((data[pos] << 8) + ((repeat_rel_offset & 0x7F) << 1)) >> 1
                pos += 1

            result += data[pos:pos + repeat_rel_offset]
            pos += repeat_rel_offset

            if pos < len(data):
                repeat_byte = bytes(result[-1:])
                repeat_count = data[pos]
                pos += 1

                if repeat_count > 0x7F:
                    repeat_count = ((data[pos] << 8) + ((repeat_count & 0x7F) << 1)) >> 1
                    pos += 1

                result += repeat_byte * repeat_count
        return result

    def __getitem__(self, key):
        return self.__records[key]
