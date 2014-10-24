import os

from tpsread import TPS

if __name__ == '__main__':
    for topdir, dirs, files in sorted(os.walk('./testdata/')):
        for filename in files:
            if filename.lower().endswith('c.tps'):
                print(os.path.join(topdir, filename))
                # try:
                tps = TPS(os.path.join(topdir, filename), encoding='cp1251', check=True, current_tablename=b'UNNAMED')
                for record in tps:
                    print(record)

                    #unittest
                    #pep8
                    #Docs (+comment)
                    #readme
                    #pydoc
                    #Profiler

                    #metadata field
                    #load in memory