import os
import importlib.util

from .__init__ import BaseBuilder, __version__

def loadPackFile():
    packFile = os.path.join(os.getcwd(), 'pack.py')
    if not os.path.exists(packFile):
        raise FileNotFoundError(f"Could not find pack file at {packFile}")
    spec = importlib.util.spec_from_file_location("pack", packFile)
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    return pack

def main():
    pack = loadPackFile()
    BaseBuilder._BaseBuilder__execute()