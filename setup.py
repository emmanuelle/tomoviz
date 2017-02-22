from distutils.core import setup
try:
    import setuptools
except ImportError:
    pass
import tomoviz

setup(name='tomoviz',
      version='0.1',
      packages=['tomoviz'],
      author='Emmanuelle Gouillart',
      author_email='emmanuelle.gouillart@gmail.com',
      url='https://github.com/emmanuelle/tomoviz',
      description="Mayavi 4D visualization"
      )

