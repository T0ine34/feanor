from src.__init__ import BaseBuilder #this file use the module to build itself


class Builder(BaseBuilder):
    def Setup(self):
        self.addDirectory('src', 'src/builderTool')
        self.addAndReplaceByPackageVersion('pyproject.toml')
        self.addFile('readme.md')
        self.venv().install('build')
        
    def Build(self):
        self.venv().runModule(f'build --outdir {self.distDir} .')


