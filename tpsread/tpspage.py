"""
TPS File Page
"""

from warnings import warn

from construct import Array, Byte, Struct, ULInt16, ULInt32

from .utils import check_value


# Page header
PAGE_HEADER_STRUCT = Struct('page',
                            ULInt32('offset'),
                            # size - total size with header
                            ULInt16('size'),
                            ULInt16('uncompressed_size'),
                            # ??? self.uncompressed_unabridged_size strange value
                            ULInt16('uncompressed_unabridged_size'),
                            ULInt16('record_count'),
                            Byte('hierarchy_level'), )


class TpsPage:
    def __init__(self, tps, ref, parent_ref, check=False):
        self.tps = tps
        self.__ref = ref
        self.parent_ref = parent_ref
        self.check = check
        self.__page_child_ref = []

        self.tps.seek(ref * 0x100 + self.tps.header.size)
        page = PAGE_HEADER_STRUCT.parse(self.tps.read(PAGE_HEADER_STRUCT.sizeof()))

        if page.hierarchy_level != 0:
            page.data = Array(lambda ctx: page.record_count, ULInt32('page_child_ref')).parse(
                self.tps.read(page.size - PAGE_HEADER_STRUCT.sizeof()))

        self.offset = page.offset
        self.size = page.size
        self.uncompressed_size = page.uncompressed_size
        self.uncompressed_unabridged_size = page.uncompressed_unabridged_size
        self.record_count = page.record_count
        self.hierarchy_level = page.hierarchy_level
        if self.hierarchy_level != 0:
            self.__page_child_ref = page.data

        if self.check:
            check_value('page_offset', self.offset, ref * 0x100 + self.tps.header.size)

    @property
    def ref(self):
        return self.__ref

    @property
    def children(self):
        return self.__page_child_ref


class TpsPagesList:
    # tree-like structure
    def __init__(self, tps, root_ref, check=False):
        self.tps = tps
        self.root_page_ref = root_ref
        self.check = check
        self.__pages = {}

        self.__add(self.root_page_ref, check=self.check)

        for current_page_ref in self.__generator(self.root_page_ref):

            if self.__pages[current_page_ref].hierarchy_level != 0:
                # Control page
                for child_page_ref in self.__pages[current_page_ref].children:
                    new_page = self.__add(child_page_ref, parent_ref=current_page_ref, check=self.check)
                    # check page inside block
                    if self.check:
                        new_page_end_ref = (new_page.offset + new_page.size - self.tps.header.size) / 0x100
                        if not self.tps.block_contains(child_page_ref, new_page_end_ref):
                            warn('Not exist block, that contains page ref# {page_ref}'
                                 .format(page_ref=child_page_ref))

    def __add(self, ref, parent_ref=None, check=False):
        page = TpsPage(self.tps, ref, parent_ref, check)

        if self.check:
            intersection_page = self.__intersection(ref, page.size)
            if intersection_page is not None:
                warn('Page ref# {page_ref1} intersects with the page ref# {page_ref2}'
                     .format(page_ref1=ref, page_ref2=intersection_page.ref))

        self[ref] = page

        return page

    def list(self):
        return list(self.__pages)

    def __generator(self, ref):
        yield ref
        queue = self[ref].children
        while queue:
            yield queue[0]
            expansion = self[queue[0]].children
            queue = expansion + queue[1:]

    def __intersection(self, ref, size):
        start_offset = ref * 0x100 + self.tps.header.size
        end_offset = start_offset + size
        for current_page_ref in self.__pages:
            current_page_end_offset = self.__pages[current_page_ref].offset + self.__pages[current_page_ref].size
            if not (not (self.__pages[current_page_ref].offset <= start_offset < current_page_end_offset) and not (
                            self.__pages[current_page_ref].offset < end_offset <= current_page_end_offset)):
                return current_page_ref
        return None

    def __getitem__(self, ref):
        return self.__pages[ref]

    def __setitem__(self, ref, item):
        self.__pages[ref] = item
