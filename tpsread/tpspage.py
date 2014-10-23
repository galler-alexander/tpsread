"""
TPS File Page
"""


class TpsPage:
    def __init__(self, tps, ref, parent_ref, check=False):
        self.tps = tps
        self.__ref = ref
        self.parent_ref = parent_ref
        self.check = check
        self.__page_child_ref = []


class TpsPagesList:
    # tree-like structure
    def __init__(self, tps, root_ref, check=False):
        self.tps = tps
        self.root_page_ref = root_ref
        self.check = check
        self.__pages = {}

    def list(self):
        return list(self.__pages)

    def __getitem__(self, ref):
        return self.__pages[ref]