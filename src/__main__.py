import os
import importlib.util
import importlib
from pathlib import Path

from .__init__ import BaseBuilder

def loadPackFile(filePath) -> Path:
    """
    Load the pack file and execute it
    Return the absolute path to the pack file
    """
    packFile = os.path.join(os.getcwd(), filePath)
    if not os.path.exists(packFile):
        raise FileNotFoundError(f"Could not find pack file at {packFile}")
    spec = importlib.util.spec_from_file_location("pack", packFile)
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    return Path(packFile)

def main() -> None:
    argumentParser = BaseBuilder.config_args()
    args = BaseBuilder.pre_parse_args(argumentParser)
    pathsBase = loadPackFile(vars(args)['build-file'])
    BaseBuilder.execute(argumentParser, pathsBase.parent)
    

if __name__ == '__main__':
    main()