"""
Class to read TPS files

http://www.clarionlife.net/content/view/41/29/
http://www.softvelocity.com/clarion/pdf/languagereferencemanual.pdf
"""

import os.path
import mmap
from datetime import date
import time
import warnings

from six import text_type
from construct import adapters, Array, Byte, Bytes, Const, Struct, UBInt32, \
    ULInt16, ULInt32

from .tpscrypt import TpsDecryptor
from .tpstable import TpsTablesList
from .tpspage import TpsPagesList
from .tpsrecord import TpsRecordsList







# TPS file header
header = Struct('header',
                ULInt32('offset'),
                ULInt16('size'),
                ULInt32('file_size'),
                ULInt32('allocated_file_size'),
                Const(Bytes('top_speed_mark', 6), b'tOpS\x00\x00'),
                UBInt32('last_issued_row'),
                ULInt32('change_count'),
                ULInt32('page_root_ref'),
                Array(lambda ctx: (ctx['size'] - 0x20) / 2 / 4, ULInt32('block_start_ref')),
                Array(lambda ctx: (ctx['size'] - 0x20) / 2 / 4, ULInt32('block_end_ref')),
)

# Date structure
date_struct = Struct('date_struct',
                     Byte('day'),
                     Byte('month'),
                     ULInt16('year'),
)

# Time structure
time_struct = Struct('time_struct',
                     Byte('centisecond'),
                     Byte('second'),
                     Byte('minute'),
                     Byte('hour')
)


class TPS:
    """
    TPS file
    """

    def __init__(self, filename, encoding=None, password=None, check=False, current_tablename=None, date_fieldname=[],
                 time_fieldname=[], decryptor_class=TpsDecryptor):
        self.filename = filename
        self.encoding = encoding
        self.password = password
        self.check = check
        self.current_table_number = None
        # Name part before .tps
        self.name = os.path.basename(filename)
        self.name = text_type(os.path.splitext(self.name)[0]).lower()
        self.date_fieldname = date_fieldname
        self.time_fieldname = time_fieldname
        self.tables = TpsTablesList()

        if not os.path.isfile(self.filename):
            raise FileNotFoundError(self.filename)

        self.file_size = os.path.getsize(self.filename)

        # Check file size
        if check:
            if self.file_size & 0x3F != 0:
                # TODO check translate
                warnings.warn('File size is not a multiple of 64 bytes.', RuntimeWarning)

        with open(self.filename, mode='r+b') as tpsfile:
            self.tps_file = mmap.mmap(tpsfile.fileno(), 0)

            self.decryptor = decryptor_class(self.tps_file, self.password)

            try:
                self.header = header.parse(self.__read(0x200))
                self.pages = TpsPagesList(self, self.header.page_root_ref, check=self.check)
                self.__getdefinition()
                self.set_current_table(current_tablename)
            except adapters.ConstError:
                print('Bad cryptographic keys.')

    def __getdefinition(self):
        for page_ref in reversed(self.pages.list()):
            if self.pages[page_ref].hierarchy_level == 0:
                for record in TpsRecordsList(self, self.pages[page_ref], check=self.check):
                    if record.type != 'NULL' and record.data.table_number not in self.tables.get_numbers():
                        self.tables.add(record.data.table_number)
                    if record.type == 'TABLE_NAME':
                        self.tables.set_name(record.data.table_number, record.data.table_name)
                    if record.type == 'TABLE_DEFINITION':
                        self.tables.add_definition(record.data.table_number, record.data.table_definition_bytes)
                    if self.tables.iscomplete():
                        break
            if self.tables.iscomplete():
                break

    def __read(self, size, pos=None):
        if pos is not None:
            self.__seek(pos)
        else:
            pos = self.tps_file.tell()
        if self.decryptor.is_encrypted():
            return self.decryptor.decrypt(size, pos)
        else:
            return self.tps_file.read(size)

    def __seek(self, pos):
        self.tps_file.seek(pos)

    def __iter__(self):
        # TODO
        pass

    def set_current_table(self, tablename):
        self.current_table_number = self.tables.get_number(tablename)

    def to_date(value):
        value_date = date_struct.parse(value)
        if value_date.year == 0:
            return None
        else:
            return date(value_date.year, value_date.month, value_date.day)

    def to_time(value):
        value_time = time_struct.parse(value)
        return time(value_time.hour, value_time.minute, value_time.second, value_time.centisecond * 10000)

        # metadata
        # ?header
        # tables
        # fields
        # longname fields
        #indexes (and key)
        #memos (and blob)

        #records
        #data
        #index

        #other
        #dimension
        #group

# utils
# convert date
# convert time
