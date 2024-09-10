import random
import sys
import os
from string import ascii_lowercase
import shutil as sh

from gamuLogger import Logger

Logger.setModule("Temp")

TEMP = os.environ['TEMP'] if 'TEMP' in os.environ else '/tmp'

def getRandomPath():
    return os.path.join(TEMP, ''.join(random.choice(ascii_lowercase) for _ in range(10)))

class TempFile:
    def __init__(self):
        self.path = getRandomPath()
        self.file = None

    def __enter__(self):
        self.file = open(self.path, 'w')
        self.file.close()
        Logger.deepDebug(f"TempFile: {self.path} created")
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.path)
        Logger.deepDebug(f"TempFile: {self.path} removed")

class TempDir:
    def __init__(self):
        self.path = getRandomPath()
        
    def create(self):
        # warning: this method is not safe to use with the with statement
        # don't forget to remove the directory
        os.mkdir(self.path)
        Logger.deepDebug(f"TempDir: {self.path} created")
        return self.path
    
    def remove(self):
        sh.rmtree(self.path)
        Logger.deepDebug(f"TempDir: {self.path} removed")

    def __enter__(self):
        return self.create()

    def __exit__(self, exc_type, exc_value, traceback):
        return self.remove()
        