import argparse
import os, sys, shutil
from enum import Enum
import importlib.metadata

from gamuLogger import Logger, LEVELS

from feanorTempDir import TempFile, TempDir

from .virtualEnv import Venv

Logger.setModule('Builder')

feanorVersion = importlib.metadata.version('feanor')
gamuLoggerVersion = importlib.metadata.version('gamuLogger')

class AbstractClassError(Exception):
    def __init__(self, message):
        super().__init__(message)
        
    def __str__(self) -> str:
        return self.message

class BaseBuilder:
    """
Create a new builder by subclassing this class and implementing the steps as methods
steps are:
- Setup
- Build
- Tests
- BuildTests
- Docs
- Publish (optional)(default: disabled)

example:
```python
class Builder(BaseBuilder):
    def Setup(self):
        #do something
    def Build(self):
        #do something
```

Use `python {your_script}.py -h` to see the available options
"""

    class Status(Enum):
        WAITING = 0
        RUNNING = 1
        FINISHED = 2
        FAILED = 3
        DISABLED = 4
        
        def __str__(self):
            return self.name
        
    class RequireMode(Enum):
        OPTIONAL = 0
        REQUIRED = 1
        
        def __str__(self):
            return self.name
        
    class ArgumentAction(Enum):
        STORE = 'store'
        STORE_TRUE = 'store_true'
        STORE_FALSE = 'store_false'
        STORE_CONST = 'store_const'
        APPEND = 'append'
        APPEND_CONST = 'append_const'
        COUNT = 'count'
        
        def __str__(self):
            return self.value
    
    __CustomArgs = {} #type: dict[str, tuple[str, str, any, str]]
    
    def __init__(self, args : dict[str, any], custom_args : dict[str, any], pathBase : str):
        if self.__class__ == BaseBuilder:
            raise AbstractClassError('BaseBuilder is an abstract class and cannot be instantiated')

        self.__args = args
        self.__custom_args = custom_args
        
        self.__pathBase = pathBase

        self.__hasExpectedExport = False

        self.__temp_dir = TempDir()
        self.__temp_dir.create()

        self.__steps = {
            "Setup":        self.Status.WAITING,
            "Build":        self.Status.DISABLED    if self.__args["no_build"] else self.Status.WAITING,
            "Tests":        self.Status.DISABLED    if self.__args["no_tests"]   else self.Status.WAITING,
            "BuildTests" :  self.Status.DISABLED    if self.__args["no_tests"]   else self.Status.WAITING,
            "Docs":         self.Status.DISABLED    if self.__args["no_docs"]   else self.Status.WAITING,
            "Publish":      self.Status.WAITING     if self.__args["publish"]   else self.Status.DISABLED
        }

        self.__clean_enabled = not self.__args["no_clean"]

        self.__remainingSteps = [step for step in self.__steps if self.__steps[step] != self.Status.DISABLED]

        self.__stepDependencies = {
            "Setup": {},
            "Build": {
                "Setup" : self.RequireMode.REQUIRED,
                "Tests" : self.RequireMode.OPTIONAL
            },
            "Docs": {
                "Setup" : self.RequireMode.REQUIRED
            },
            "Tests": {
                "Setup" : self.RequireMode.REQUIRED
            },
            "BuildTests": {
                "Setup" : self.RequireMode.REQUIRED,
                "Build" : self.RequireMode.REQUIRED
            },
            "Publish": {
                "Build" : self.RequireMode.REQUIRED,
                "BuildTests" : self.RequireMode.OPTIONAL,
                "Docs" : self.RequireMode.OPTIONAL
            }
        } #type: dict[str, dict[str, BaseBuilder.RequireMode]]

        self.__debugLevel = LEVELS.INFO

        if self.__args["debug"]:
            self.__debugLevel = LEVELS.DEBUG
        elif self.__args["deep_debug"]:
            self.__debugLevel = LEVELS.DEEP_DEBUG

        Logger.setLevel('stdout', self.__debugLevel)

        Logger.debug(f"Using python version : {sys.version}")
        Logger.debug(f"Using feanor version : {feanorVersion}")
        Logger.debug(f"Using gamuLogger version : {gamuLoggerVersion}")
        Logger.debug(f'Using temporary directory: {os.path.abspath(self.__temp_dir.path)}')
        Logger.debug('Using distribution directory: ' + os.path.abspath(self.__args["dist_dir"]))

        # clear the dist directory
        try:
            shutil.rmtree(self.__args["dist_dir"])
        except FileNotFoundError:
            pass
        except Exception as e:
            Logger.error(f'Error while cleaning dist directory: {str(e)}')
            sys.exit(1)

        os.makedirs(self.__args["dist_dir"], exist_ok=True)


#region PUBLIC PROPERTIES

    @property
    def tempDir(self):
        """The path to the temporary directory"""
        return self.__temp_dir.path
    
    @property
    def packageVersion(self):
        """The version of the package the user wants to build"""
        return self.__args["package_version"]

    @property
    def pathBase(self):
        """The from where are resolved relative paths in the source code (i.e. not the temporary directory)"""
        return self.__pathBase
    
    @property
    def distDir(self):
        """The path to the distribution directory (by default, it's the 'dist' directory located in the current working directory)"""
        self.__hasExpectedExport = True
        return self.__distDir


#endregion
#region PUBLIC FUNCTIONS


    def addAndReplaceByPackageVersion(self, src, dest = None, versionString = "{version}"):
        """Add a file to the temporary directory and replace all occurrences of versionString in it  by the package version"""
        if dest is None:
            dest = src
        if not os.path.isabs(src):
            src = os.path.join(self.pathBase, src)
        Logger.debug(f'Adding file: {src} and replacing version string by {self.packageVersion}')
        with open(src, 'r') as file:
            content = file.read()
        content = content.replace(versionString, self.packageVersion)
        
        with open(f'{self.tempDir}/{dest}', 'w') as file:
            file.write(content)
        return True

    def runCommand(self, command : str, hideOutput = True, debugArg = "", deepDebugArg : str = None) -> bool:
        """
        Execute a command in the temporary directory\n
        Default value for deepDebugArg is the same as debugArg\n
        Return whether the command has succeeded or not
        """
        if self.__debugLevel == LEVELS.DEBUG:
            command += f" {debugArg}"
        elif self.__debugLevel == LEVELS.DEEP_DEBUG:
            command += " " + (deepDebugArg if deepDebugArg is not None else debugArg)
        Logger.debug(f'Executing command {command}\n    working directory: {self.tempDir}')
        if hideOutput:

            with TempFile() as stdoutPath, TempFile() as stderrPath:

                cwd = os.getcwd()
                os.chdir(self.tempDir)
                returnCode = os.system(f'{command} > {stdoutPath} 2> {stderrPath}')
                os.chdir(cwd)

                if returnCode != 0:
                    Logger.error(f'Task failed with return code {returnCode}')
                    with open(stdoutPath, 'r') as file:
                        Logger.debug('stdout:\n' + file.read())
                    with open(stderrPath, 'r') as file:
                        Logger.debug('stderr:\n' + file.read())

                    raise RuntimeError('Command failed')
                else:
                    Logger.debug('Command executed successfully')
                    return True

        else:
            returnCode = os.system(f'{command}')
            if returnCode != 0:
                Logger.error(f'Task failed with return code {returnCode}')
                raise RuntimeError('Command failed')
            else:
                Logger.debug('Command executed successfully')
                return True

    def addFile(self, path, dest = None):
        """Copy a file to the temporary directory"""
        if dest is None:
            dest = path
        if not os.path.isabs(path):
            path = os.path.join(self.pathBase, path)
        Logger.debug(f'Adding file: {path}')
        shutil.copy(path, f'{self.tempDir}/{dest}')
        return True   

    def addDirectory(self, path, dest = None):
        """Copy a directory to the temporary directory"""
        if dest is None:
            dest = path
        if not os.path.isabs(path):
            path = os.path.join(self.pathBase, path)
        Logger.debug(f'Adding directory: {path}')
        shutil.copytree(
            path,
            f'{self.tempDir}/{dest}',
            ignore=shutil.ignore_patterns('*.pyc', '*.pyo', '__pycache__'),
        )
        return True

    def exportFile(self, path, dest = None):
        """Copy a file from the temporary directory to the distribution directory"""
        self.__hasExpectedExport = True
        if os.path.exists(f'{self.tempDir}/{path}'):
            Logger.debug(f'Exporting file: {path}')
            if dest is None:
                dest = path
            shutil.copy(f'{self.tempDir}/{path}', f'{self.__distDir}/{dest}')
            return True
        else:
            Logger.warning(f'Trying to export a file that does not exist: {path}')
            return False
    
    def exportFolderContent(self, path, dest = None):
        """Copy the content of a directory from the temporary directory to the distribution directory"""
        self.__hasExpectedExport = True
        if os.path.exists(f'{self.tempDir}/{path}'): #check if the directory exists
            if os.listdir(f'{self.tempDir}/{path}'): #check if the directory is not empty
                Logger.debug(f'Exporting directory content: {path}')
                if dest is None:
                    dest = path
                for root, _, filenames in os.walk(f'{self.tempDir}/{path}'):
                    for filename in filenames:
                        shutil.copy(os.path.join(root, filename), f'{self.__distDir}/{filename}')

                return True
            else:
                Logger.warning(f'Trying to export the content of an empty directory: {path}')
                return False
        else:
            Logger.warning(
                f'Trying to export the content of a directory that does not exist: {path}'
            )
            return False

    def exportFolder(self, path, dest = None):
        """Copy a directory from the temporary directory to the distribution directory"""
        self.__hasExpectedExport = True
        if os.path.exists(f'{self.tempDir}/{path}'): #check if the directory exists
            Logger.debug(f'Exporting directory: {path}')
            if dest is None:
                dest = path
            shutil.copytree(f'{self.tempDir}/{path}', f'{self.__distDir}/{dest}')
            return True
        else:
            Logger.warning(f'Trying to export a directory that does not exist: {path}')
            return False
        
    def hasArg(self, arg : str) -> bool:
        """Check if an argument is present"""
        return arg in self.__custom_args
    
    def getArg(self, arg : str) -> any:
        """Get the value of an argument"""
        return self.__custom_args[arg] if self.hasArg(arg) else None

    def venv(self):
        """Create a virtual environment in the temporary directory"""
        return Venv.getInstance(f'{self.tempDir}/env', self.tempDir, self.exportFile, self.__debugLevel)


#endregion
#region STATIC FUNCTIONS


    @staticmethod
    def addArgument(argument : str, short : str = None, help : str = "", default = False, action : ArgumentAction = ArgumentAction.STORE_TRUE):
        """
        Add an argument to the command line parser
        """
        BaseBuilder.__CustomArgs[argument] = (short, help, default, str(action))


#endregion
#region PRIVATE PROPERTIES


    @property
    def __distDir(self):
        return os.path.abspath(self.__args["dist_dir"])


#endregion
#region PRIVATE FUNCTIONS


    def __clean(self) -> bool:
        Logger.info('Cleaning temporary directory')
        try:
            self.__temp_dir.remove()
        except Exception as e:
            Logger.error(f'Error while cleaning temp directory: {str(e)}')
            return False
        else:
            Logger.debug('Temporary directory cleaned')
        TempDir.cleanRemaining()
        return True
        
    def __canStepBeStarted(self, step):
        # a better version of the previous function
        for dependency, requireMode in self.__stepDependencies[step].items():
            match self.__steps[dependency]:
                case self.Status.WAITING:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is not started yet")
                    return False
                case self.Status.RUNNING:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is running and need to finish first")
                    return False
                case self.Status.FAILED:
                    Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' has failed")
                    return False
                case self.Status.DISABLED:
                    if requireMode == self.RequireMode.REQUIRED:
                        Logger.deepDebug(f"The step '{step}' cannot be started because the dependency '{dependency}' is disabled but required")
                        return False
                    else:
                        Logger.deepDebug(f"The step '{step}' will run without the optional dependency '{dependency}'")
                        continue
                case self.Status.FINISHED:
                    continue
        return True
        
    def __runStep(self, step : str):
        '''
        A step is considered failed if it raises an exception, or if it returns False
        '''
        try:
            hasSucceeded = getattr(self, step)()
        except Exception as e:
            Logger.error(f'Step "{step}" raised an exception: {str(e)}')
            return False
        else:
            return True if hasSucceeded is None else hasSucceeded
        
    def __listExport(self):
        files = []
        for root, _, filenames in os.walk(self.__distDir):
            for filename in filenames:
                abspath = os.path.join(root, filename)
                files.append(abspath.replace(f'{self.__distDir}/', ''))
        return files
    
    def __run(self, configuredSteps : list[str]):
        for step in self.__steps:
            if step not in configuredSteps:
                self.__steps[step] = self.Status.DISABLED
                if step in self.__remainingSteps:
                    self.__remainingSteps.remove(step)
                Logger.debug(f'Step "{step}" disabled')

        HasFailed = False
        while len(self.__remainingSteps) > 0 and not HasFailed:
            for step in self.__steps:
                if self.__steps[step] == self.Status.DISABLED:
                    continue
                Logger.deepDebug(f"evaluating step {step}\nremaining : {str(self.__remainingSteps)}")
                if self.__steps[step] == self.Status.WAITING and self.__canStepBeStarted(step):
                    Logger.info(f'Starting step "{step}"')
                    self.__steps[step] = self.Status.RUNNING

                    hasSucceeded = self.__runStep(step)
                    Logger.deepDebug(f'Step "{step}" returned {str(hasSucceeded)}')

                    if hasSucceeded:
                        self.__steps[step] = self.Status.FINISHED
                        self.__remainingSteps.remove(step)
                    else:
                        self.__steps[step] = self.Status.FAILED
                        Logger.error(f'Step "{step}" failed')
                        HasFailed = True
                        break

        if self.__clean_enabled:
            self.__temp_dir.keep = True
            self.__clean()
        else:
            Logger.warning(f'Directory {self.tempDir} wasn\'t deleted because cleaning is disabled')

        if HasFailed:
            Logger.critical('A step has failed')
            sys.exit(1)
        else:
            Logger.info('Build finished successfully')
            exported = self.__listExport()
            if self.__hasExpectedExport and len(exported) == 0:
                Logger.warning('It seems that no files were exported, check your export functions if you expect some files to be exported')
            elif len(exported) > 0:
                Logger.info("\n\t".join(["exported files:"]+exported))


#endregion
#region PRIVATE STATIC FUNCTIONS

    @staticmethod
    def config_args():
        argumentParser = argparse.ArgumentParser(description='Builder tool', prog="feanor", add_help=False)
        
        argumentParser.add_argument('build-file', help='The path to the build file (default : "%(default)s")', type=str, default='pack.py', nargs='?')
        
        loggerOptions = argumentParser.add_mutually_exclusive_group()
        loggerOptions.add_argument('--debug', action='store_true', help='Enable debug messages')
        loggerOptions.add_argument('--deep-debug', action='store_true', help='Enable deep debug messages')
        
        buildersOptions = argumentParser.add_argument_group('Builder options')
        buildersOptions.add_argument('--no-tests', action='store_true', help='Do not run tests')
        buildersOptions.add_argument('--no-docs', action='store_true', help='Do not generate documentation')
        buildersOptions.add_argument('--no-build', action='store_true', help='Only run tests, do not build the package')
        buildersOptions.add_argument('--publish', action='store_true', help='Publish the package')
        buildersOptions.add_argument('--no-clean', action='store_true', help='Do not clean temporary files')
        buildersOptions.add_argument('--dist-dir', help='Distribution directory (where to save the built files) (default : "%(default)s")', type=str, default='dist')
        buildersOptions.add_argument('-pv', '--package-version', help='set the version of the package you want to build (default : "%(default)s")', type=str, default='0.0.0')
        
        argumentParser.add_argument('--version', '-v', action='store_true', help='Show the version of the tool')
        argumentParser.add_argument('--help', '-h', action='store_true', help='Show this help message and exit')
        
        return argumentParser
        
    @staticmethod
    def __get_args(argumentParser : argparse.ArgumentParser):
        try:
            allArgs = argumentParser.parse_args()
        except SystemExit as e:
            Logger.error('Error while parsing arguments; use -h to see the available options')
            raise RuntimeError('Error while parsing arguments') from e
        else:
            reservedArgsKeys = ['debug', 'deep_debug', 'no_tests', 'no_build', 'no_docs', 'publish', 'no_clean', 'dist_dir', 'package_version', 'help', 'version']

            # split the args into two lists (args, custom_args)
            args = {key: value for key, value in vars(allArgs).items() if key in reservedArgsKeys}
            custom_args = {key: value for key, value in vars(allArgs).items() if key not in reservedArgsKeys}
            return args, custom_args
    
    @staticmethod
    def pre_parse_args(argumentParser : argparse.ArgumentParser):
        try:
            allArgs = argumentParser.parse_args()
        except SystemExit as e:
            Logger.error('Error while parsing arguments; use -h to see the available options')
            raise RuntimeError('Error while parsing arguments') from e
        else:
            if allArgs.version:
                Logger.info(f"feanor version : {feanorVersion}")
                sys.exit(0)
            if allArgs.help and not os.path.exists(os.path.join(os.getcwd(), vars(allArgs)['build-file'])):
                argumentParser.print_help()
                sys.exit(0)
            return allArgs
    
    @staticmethod
    def execute(argumentParser, pathBase):
        try:
            # add user defined arguments
            customOptions = argumentParser.add_argument_group('Custom options')
            for arg in BaseBuilder.__CustomArgs:
                short, helpMessage, default, action = BaseBuilder.__CustomArgs[arg]
                if not arg.startswith('--'):
                    arg = f'--{arg}'
                if short is not None:
                    if len(short) > 2:
                        Logger.error(f'Short argument must be one or two characters long (found "{short}")')
                        return
                    if not short.startswith('-'):
                        short = f'-{short}'
                    customOptions.add_argument(short, arg, help=helpMessage, default=default, action=action)
                else:
                    customOptions.add_argument(arg, help=helpMessage, default=default, action=action)

            args, custom_args = BaseBuilder.__get_args(argumentParser)

            if 'version' in args and args['version']:
                Logger.info(f"feanor version : {feanorVersion}")
                return
            if 'help' in args and args['help']:
                argumentParser.print_help()
                return
                
        except RuntimeError:
            Logger.critical('Error while parsing arguments')
            return

        else:
            subClasses = BaseBuilder.__subclasses__()
            if len(subClasses) == 0:
                Logger.critical('No builders found')
                return
            elif len(subClasses) > 1:
                Logger.critical('Multiple builders found')
                return

            builderClass = subClasses[0]

            possibleSteps = {'Setup', 'Tests', 'BuildTests', 'Docs', 'Build', 'Publish'}

            authorizedElements = {'__doc__', '__module__'}.union(possibleSteps)
            for element in builderClass.__dict__:
                if element not in authorizedElements:
                    Logger.warning(f'Unknown element in builder class: "{element}"; ignoring it')

            steps = [step for step in builderClass.__dict__ if step in possibleSteps]
            builderInstance = builderClass(args, custom_args, pathBase)
            builderInstance.__run(steps)
        
#endregion
