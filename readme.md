# Fëanor

## Description

Python script for simplify automatic build, tests, publish and deploy of projects.
- only one file to create
- based on python classes
- easy to use
- compatible with any language
- usable in CI/CD pipelines
- clear logs for debugging
- build from a temporary directory, so the source code is not modified
- fully support python virtual environments, useful for python projects
- can process custom arguments, for set up a conditional build for example
- choose the files you want to export from the build

## Usage
create a file named `pack.py` in the root of your project with the following content:

```python
from feanor import BaseBuilder

class Builder(BaseBuilder):
    def Setup(self):
        pass

    def Tests(self):
        pass

    def Docs(self):
        pass
        
    def Build(self):
        pass

    def BuildTests(self):
        pass

    def Publish(self):
        pass
        
```

> You can rename the `Builder` class to any name you want.

> You can rename the file to any name you want.

> Remove the methods that you don't need (`Setup` and `Build` are the only required methods).

run the script with:
```bash
python pack.py
```

### Options
use ```python pack.py --help``` to see the available options:

```
-h, --help            show this help message and exit
  --debug               Enable debug messages
  --deep-debug          Enable deep debug messages
  --version, -v         show program's version number and exit

Builder options:
  --no-tests            Do not run tests
  --no-docs             Do not generate documentation
  --publish             Publish the package
  --no-clean            Do not clean temporary files
  --dist-dir DIST_DIR   Distribution directory (where to save the built files)
  -pv PACKAGE_VERSION, --package-version PACKAGE_VERSION
                        set the version of the package you want to build
```
