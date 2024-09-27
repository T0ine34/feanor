from feanor import BaseBuilder


class Builder(BaseBuilder):
    def Setup(self):
        self.addDirectory('src', 'src/feanor')
        self.addAndReplaceByPackageVersion('src/__init__.py', 'src/feanor/__init__.py')
        self.addAndReplaceByPackageVersion('pyproject.toml')
        self.addFile('readme.md')
        self.venv().install('build')
        
    def Build(self):
        self.venv().runModule(f'build --outdir {self.distDir} .')

