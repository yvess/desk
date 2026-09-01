import re
from pathlib import Path

from setuptools import setup, find_packages

# Read the version without importing desk -- importing it would pull in the
# runtime dependencies, which are absent from pip's isolated build environment.
version_file = Path(__file__).parent / 'desk' / '__init__.py'
version_match = re.search(
    r"^__version__ = ['\"]([^'\"]+)['\"]",
    version_file.read_text(), re.MULTILINE
)
if version_match is None:
    raise RuntimeError(f"__version__ not found in {version_file}")
version = version_match.group(1)

setup(
    name='desk',
    version=version,
    license="BSD",

    # install_requires=[
    #     "django>=1.4.0",
    # ],

    description="desk, service data manager",
    #long_description=open('README.rst').read(),

    author='Yves Serrano',
    author_email='ys@taywa.ch',

    url='http://github.com/yvess/desk',
    download_url='http://github.com/yvess/desk/downloads',

    include_package_data=True,

    packages=find_packages(),

    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        #'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
