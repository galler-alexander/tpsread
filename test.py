import os
from datetime import datetime

from tpsread import TPS


if __name__ == '__main__':
    print(datetime.now())
    for topdir, dirs, files in sorted(os.walk('./testdata/')):
        for filename in files:
            if filename.lower().endswith('.tps'):
                print(os.path.join(topdir, filename))
                # try:
                tps = TPS(os.path.join(topdir, filename), encoding='cp1251', cached=True, check=True,
                          current_tablename='UNNAMED')
                print(datetime.now())
                for record in tps:
                    # print(record)
                    pass

    print(datetime.now())

                    #unittest
                    #pep8
                    #Docs (+comment)
                    #readme
                    #pydoc
                    #Profiler

                    #metadata field
                    #load in memory