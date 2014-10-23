class TpsRecordsList:
    def __init__(self, tps, tps_page, check=False):
        self.tps = tps
        self.check = check
        self.tps_page = tps_page
        self.__records = []

    def __getitem__(self, key):
        return self.__records[key]