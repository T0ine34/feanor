import os
import importlib.util
import importlib
from types import ModuleType

from .__init__ import BaseBuilder

def loadPackFile() -> ModuleType:
    packFile = os.path.join(os.getcwd(), 'pack.py')
    if not os.path.exists(packFile):
        raise FileNotFoundError(f"Could not find pack file at {packFile}")
    spec = importlib.util.spec_from_file_location("pack", packFile)
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    return pack

def main() -> None:
    pack = loadPackFile()
    BaseBuilder.execute()
    

if __name__ == '__main__':
    main()