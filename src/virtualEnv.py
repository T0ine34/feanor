from gamuLogger import Logger, LEVELS
import sys, os
from feanorTempDir import TempFile
import json
from typing import Callable


PYTHON = sys.executable #type: str
NULL_TARGET = '/dev/null' if os.name == 'posix' else 'nul' #type: str
IS_POSIX = os.name == 'posix' #type: bool

Logger.setModule("VirtualVenv")

class Venv:
    """
    Class to manage a virtual environment
    Only one instance of this class should be created
    """
    __instance = None
    
    def __init__(self, path : str, workingDir : str, exportFileMethod : Callable[[str], bool], debugLevel : LEVELS = LEVELS.INFO):
        self.__path = path
        self.__workingDir = workingDir
        self.__debugLevel = debugLevel
        self.__exportFile = exportFileMethod
        
        self.binDir = 'bin' if IS_POSIX else 'Scripts'
        
        Logger.deepDebug("executing command: " + f'"{PYTHON}" -m venv {path}')
        returnCode = os.system(f'"{PYTHON}" -m venv {path}')
        if returnCode != 0:
            Logger.error(f'Command "{PYTHON}" -m venv {path} failed with return code {returnCode}')
            sys.exit(returnCode)
        Logger.deepDebug(f'Command "{PYTHON}" -m venv {path} executed successfully')
        
        Venv.__instance = self
        
#region PROPERTIES

    @property
    def python(self):
        """the path to the python executable in the virtual environment"""
        return os.path.join(self.__path, self.binDir, 'python')
    
    @property
    def pip(self):
        """the path to the pip executable in the virtual environment"""
        return os.path.join(self.__path, self.binDir, 'pip')

    @property
    def path(self):
        """the path to the virtual environment"""
        return self.__path
        

#endregion
#region PUBLIC FUNCTIONS
        
        
    def install(self, package : str, version = None):
        """Install a package in the virtual environment\n
        Return the instance to chain the calls"""
        if version is not None:
            package += f'=={version}'
        Logger.debug(f"Installing package {package}")
        self.__run(f'python -m pip install {package}')
        Logger.debug(f"Package {package} installed successfully")
        return self #to chain the calls
        
    def InstallFromRequirements(self, path : str):
        """Install packages from a requirements file"""
        Logger.debug(f"Installing packages from requirements file {path}")
        self.__run('python', '-m', 'pip', 'install', '-r', path)
        Logger.debug(f"Packages installed successfully")
        
    def runExecutable(self, executable : str, *args : str):
        """Run an executable in the virtual environment\n
        Can be used to run module who create an executable\n
        """
        Logger.debug(f"Running executable {executable} with arguments {' '.join(args)} in virtual environment (working directory: {self.__workingDir})")
        self.__run(executable, *args)
        Logger.debug(f"Executable {executable} executed successfully")
        return self
    
    def runModule(self, module : str, *args : str):
        """Run a module in the virtual environment\n
        ```python
        venv.runModule('module')
        ```
        is equivalent to
        ```
        python -m module
        ```
        """
        Logger.debug(f'Running module "{module}" with arguments {" ".join(args)} in virtual environment (working directory: {self.__workingDir})')
        self.__run('python', '-m', module, *args)
        Logger.debug(f"Module {module} executed successfully")
        return self
    
    def runMelkor(self, configFile : str):
        """Install and run melkor module in the virtual environment
        > the config file must be added to the temp directory before calling this function
        > don't forget to export the report file generated by melkor
        """
        self.install('melkor')

        cwd = os.getcwd()
        os.chdir(self.__workingDir)
        cmd = os.path.join(self.__path, self.binDir, 'melkor') + ' ' + configFile
        if self.__debugLevel in [LEVELS.DEBUG, LEVELS.DEEP_DEBUG]:
            cmd += ' --debug'
        returnCode = os.system(cmd)
        os.chdir(cwd) # reset the working directory
        
        # export the report file
        # read the config file to get the report file name
        with open(configFile, 'r') as file:
            data = json.load(file)
        reportFile = data['outFile']
        if os.path.exists(reportFile):
            Logger.debug(f'Exporting report file {reportFile}')
            self.__exportFile(reportFile)
        else:
            Logger.error(f"Report file {reportFile} not found")
        
        if returnCode != 0:
            Logger.error(f'Melkor tests failed with return code {returnCode}')
            raise RuntimeError('Melkor tests failed')
        

#endregion
#region STATIC FUNCTIONS


    @staticmethod
    def getInstance(path : str, workingDir : str, exportFileMethod : Callable[[str], bool], debugLevel : LEVELS = LEVELS.INFO):
        """Get the instance of the virtual environment, create it if it doesn't exist"""
        if Venv.__instance is None:
            Logger.debug("Creating new Venv instance")
            Venv.__instance = Venv(path, workingDir, exportFileMethod, debugLevel)
        return Venv.__instance

#endregion
#region PRIVATE FUNCTIONS

        
    def __run(self, command : str, *args : str):
        with TempFile() as stdoutPath, TempFile() as stderrPath:
            
            if len(args) > 0:
                command += ' ' + ' '.join(args)
        
            Logger.deepDebug(f'executing command: "{os.path.join(self.__path, self.binDir, command)}"')
            
            cwd = os.getcwd()
            os.chdir(self.__workingDir)
            returnCode = os.system(f'{os.path.join(self.__path, self.binDir, command)} > {stdoutPath} 2> {stderrPath}')
            os.chdir(cwd)
            
            if returnCode != 0:
                Logger.error(f'Command "{command}" failed with return code {returnCode}')
                with open(stdoutPath, 'r') as file:
                    Logger.debug('stdout:\n' + file.read())
                with open(stderrPath, 'r') as file:
                    Logger.debug('stderr:\n' + file.read())
                    
                raise RuntimeError('Command failed')
        
#endregion
