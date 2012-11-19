import gitbigfile
try:
    from setuptools import setup
    kw = {
        'install_requires': 'docopt == 0.5.0',
    }
except ImportError:
    from distutils.core import setup
    kw = {}


setup(
    name='git-bigfile',
    version=gitbigfile.__version__,
    author='Benjamin Bertrand',
    author_email='beenje@gmail.com',
    license='MIT',
    description='git-bigfile allows you to use Git with large files without storing the file in Git itself',
    long_description=open('README.rst').read(),
    url='https://github.com/beenje/git-bigfile',
    packages=['gitbigfile'],
    scripts=['bin/git-bigfile'],
    classifiers=['Development Status :: 4 - Beta',
                 'Topic :: Software Development',
                 'License :: OSI Approved :: MIT License',
                 'Intended Audience :: Developers',
                 'Programming Language :: Python'],
    **kw
)
