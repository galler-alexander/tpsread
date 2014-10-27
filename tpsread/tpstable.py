"""
TPS File Table
"""

from construct import Array, BitField, BitStruct, Byte, Const, CString, Embed, Enum, Flag, If, Padding, Struct, ULInt16

from .tpsrecord import TpsRecordsList


FIELD_TYPE_STRUCT = Enum(Byte('type'),
                         BYTE=0x1,
                         SHORT=0x2,
                         USHORT=0x3,
                         # date format 0xYYYYMMDD
                         DATE=0x4,
                         # time format 0xHHMMSSHS
                         TIME=0x5,
                         LONG=0x6,
                         ULONG=0x7,
                         FLOAT=0x8,
                         DOUBLE=0x9,
                         DECIMAL=0x0A,
                         STRING=0x12,
                         CSTRING=0x13,
                         PSTRING=0x14,
                         # compound data structure
                         GROUP=0x16,
                         # LIKE (inherited data type)
)

TABLE_DEFINITION_FIELD_STRUCT = Struct('record_table_definition_field',
                                       FIELD_TYPE_STRUCT,
                                       # data offset in record
                                       ULInt16('offset'),
                                       CString('name'),
                                       ULInt16('array_element_count'),
                                       ULInt16('size'),
                                       # 1, if fields overlap (OVER attribute), or 0
                                       ULInt16('overlaps'),
                                       # record number
                                       ULInt16('number'),
                                       If(lambda x: x['type'] == 'STRING', ULInt16('array_element_size')),
                                       If(lambda x: x['type'] == 'STRING', ULInt16('template')),
                                       If(lambda x: x['type'] == 'CSTRING', ULInt16('array_element_size')),
                                       If(lambda x: x['type'] == 'CSTRING', ULInt16('template')),
                                       If(lambda x: x['type'] == 'PSTRING', ULInt16('array_element_size')),
                                       If(lambda x: x['type'] == 'PSTRING', ULInt16('template')),
                                       If(lambda x: x['type'] == 'PICTURE', ULInt16('array_element_size')),
                                       If(lambda x: x['type'] == 'PICTURE', ULInt16('template')),
                                       If(lambda x: x['type'] == 'DECIMAL', Byte('decimal_count')),
                                       If(lambda x: x['type'] == 'DECIMAL', Byte('decimal_size')),
                                       allow_overwrite=True, )

INDEX_TYPE_STRUCT = Enum(BitField('type', 2),
                         KEY=0,
                         INDEX=1,
                         DYNAMIC_INDEX=2)

INDEX_FIELD_ORDER_TYPE_STRUCT = Enum(ULInt16('field_order_type'),
                                     ASCENDING=0,
                                     DESCENDING=1,
                                     _default_='DESCENDING')

TABLE_DEFINITION_INDEX_STRUCT = Struct('record_table_definition_index',
                                       # May be external_filename
                                       # if external_filename == 0, no external file index
                                       CString('external_filename'),
                                       If(lambda x: len(x['external_filename']) == 0, Const(Byte('index_mark'), 1)),
                                       CString('name'),
                                       Embed(BitStruct('flags',
                                                       Padding(1),
                                                       INDEX_TYPE_STRUCT,
                                                       Padding(2),
                                                       Flag('NOCASE'),
                                                       Flag('OPT'),
                                                       Flag('DUP'))),
                                       ULInt16('field_count'),
                                       Array(lambda x: x['field_count'],
                                             Struct('index_field_propertly',
                                                    ULInt16('field_number'),
                                                    INDEX_FIELD_ORDER_TYPE_STRUCT)), )

MEMO_TYPE_STRUCT = Enum(Flag('memo_type'),
                        MEMO=0,
                        BLOB=1)

TABLE_DEFINITION_MEMO_STRUCT = Struct('record_table_definition_memo',
                                      # May be external_filename
                                      # if external_filename == 0, no external file index
                                      CString('external_filename'),
                                      If(lambda x: len(x['external_filename']) == 0, Const(Byte('memo_mark'), 1)),
                                      CString('name'),
                                      ULInt16('size'),
                                      Embed(BitStruct('flags',
                                                      Padding(5),
                                                      MEMO_TYPE_STRUCT,
                                                      Flag('BINARY'),
                                                      Flag('Flag'),
                                                      Padding(8))), )

TABLE_DEFINITION_STRUCT = Struct('record_table_definition',
                                 ULInt16('min_version_driver'),
                                 # sum all fields sizes in record
                                 ULInt16('record_size'),
                                 ULInt16('field_count'),
                                 ULInt16('memo_count'),
                                 ULInt16('index_count'),
                                 Array(lambda x: x['field_count'], TABLE_DEFINITION_FIELD_STRUCT),
                                 Array(lambda x: x['memo_count'], TABLE_DEFINITION_MEMO_STRUCT),
                                 Array(lambda x: x['index_count'], TABLE_DEFINITION_INDEX_STRUCT), )


class TpsTable:
    def __init__(self, number):
        self.number = number
        self.name = ''
        self.definition_bytes = {}
        self.definition = ''
        self.statistics = {}

    @property
    def iscomplete(self):
        # TODO check all parts complete
        if self.name != '':
            self.get_definition()
            return True
        else:
            return False

    def add_definition(self, definition):
        portion_number = ULInt16('portion_number').parse(definition[:2])
        self.definition_bytes[portion_number] = definition[2:]

    def add_statistics(self, statistics_struct):
        # TODO remove metadatatype from staticstics_struct
        self.statistics[statistics_struct.metadata_type] = statistics_struct

    def get_definition(self):
        definition_bytes = b''
        for value in self.definition_bytes.values():
            definition_bytes += value
        self.definition = TABLE_DEFINITION_STRUCT.parse(definition_bytes)
        return self.definition

    def set_name(self, name):
        self.name = name


class TpsTablesList:
    def __init__(self, tps, encoding=None, check=False):
        self.__tps = tps
        self.encoding = encoding
        self.check = check
        self.__tables = {}

        # get tables definition
        i = 0
        d = None
        s = None
        for page_ref in reversed(self.__tps.pages.list()):
            if self.__tps.pages[page_ref].hierarchy_level == 0:
                for record in TpsRecordsList(self.__tps, self.__tps.pages[page_ref],
                                             encoding=self.encoding, check=self.check):
                    i += 1
                    if record.type != 'NULL' and record.data.table_number not in self.__tables.keys():
                        self.__tables[record.data.table_number] = TpsTable(record.data.table_number)
                    if record.type == 'TABLE_NAME':
                        self.__tables[record.data.table_number].set_name(record.data.table_name.decode(self.encoding))
                    if record.type == 'TABLE_DEFINITION':
                        self.__tables[record.data.table_number].add_definition(record.data.table_definition_bytes)
                        #d = i
                    if record.type == 'METADATA':
                        self.__tables[record.data.table_number].add_statistics(record.data)
                        #s = i
                    #TODO optimize (table_definition and metadata(statistics))
                    if self.__iscomplete():
                        break
                if self.__iscomplete():
                    break
                    #print('stats:', i, d, s, len(self.__tps.pages.list()))
                    #TODO raise exception: No definition found

    def __iscomplete(self):
        for i in self.__tables:
            if not self.__tables[i].iscomplete:
                return False
        if len(self.__tables) == 0:
            return False
        else:
            return True

    def get_definition(self, number):
        return self.__tables[number].get_definition()

    def get_number(self, name):
        for i in self.__tables:
            if self.__tables[i].name == name:
                return i
