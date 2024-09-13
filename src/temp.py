import random
import sys
import os
from string import ascii_lowercase
import shutil as sh
from enum import Enum

from gamuLogger import Logger

Logger.setModule("Temp")

TEMP = os.environ['TEMP'] if 'TEMP' in os.environ else '/tmp'

def getRandomPath():
    """return a random path in the temporary directory, can be used to create a temporary file or directory"""
    return os.path.join(TEMP, ''.join(random.choice(ascii_lowercase) for _ in range(10)))


class State(Enum):
    INITATED = 0
    CREATED = 1
    


class TempFile:
    """A temporary file, created when entering the context and removed when exiting"""
    def __init__(self):
        self.__path = getRandomPath()
        self.__file = None
        self.__state = State.INITATED

    def __enter__(self):
        if self.__state != State.INITATED:
            Logger.error(f"Cannot create temporary file {self.__path} because it already exist")
            raise FileExistsError("File already exist")
        self.__file = open(self.path, 'w')
        self.__file.close()
        Logger.deepDebug(f"TempFile: {self.path} created")
        self.__state = State.CREATED
        return self.__path

    def __exit__(self, exc_type, exc_value, traceback):
        if self.__state != State.CREATED:
            Logger.error(f"Cannot delete temporary file {self.__path} because it wasn't created")
            raise FileNotFoundError("File doesn't exist")
        os.remove(self.__path)
        self.__file = None
        Logger.deepDebug(f"TempFile: {self.path} removed")
        self.__state = State.INITATED
        
    @property
    def path(self):
        """the path of the temporary file"""
        return self.__path



class TempDir:
    """A temporary directory, created when entering the context, or when calling the method `TempDir.create()`\n
    deleted when exiting the context, or calling the method `TempDir.remove()`
    """
    __currentTempDir : list['TempDir'] = [] # keep a trace of current active temporary directory to be able to delete them later
    
    def __init__(self):
        self.__path = getRandomPath()
        self.__state = State.INITATED
        self.__keep = True
        
    def create(self):
        if self.__state != State.INITATED:
            Logger.error(f"Cannot create temporary directory \"{self.__path}\" because it already exist")
            raise FileExistsError("Directory already exist")
        os.mkdir(self.__path)
        Logger.deepDebug(f"TempDir: {self.__path} created")
        self.__state = State.CREATED
        TempDir.__currentTempDir.append(self)
        return self.path
    
    def remove(self):
        if self.__state != State.CREATED:
            Logger.error(f"Cannot delete temporary directory  \"{self.__path}\" because it was not created")
            raise FileNotFoundError("Folder does not exist")
        sh.rmtree(self.path)
        Logger.deepDebug(f"TempDir: {self.__path} removed")
        self.__state = State.INITATED
        
        TempDir.__currentTempDir.remove(self)

    def __enter__(self):
        return self.create()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.remove()

    @property
    def keep(self):
        return self.__keep
    
    @keep.setter
    def keep(self, value : bool):
        self.__keep = value
    
    @property
    def path(self):
        """the path of the temporary directory"""
        return self.__path
        
        
    @staticmethod
    def cleanRemaining():
        for tempDir in TempDir.__currentTempDir:
            if not tempDir.keep:
                tempDir.remove()
            else:
                Logger.warning(f"the temporary directory {tempDir.path} wasn't deleted because it was asked to keep it")