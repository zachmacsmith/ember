"""
Minimal build of ONLY the minorminer._minorminer extension (the find_embedding /
miner search) for the Ember search-guidance fork. Skips busclique / subgraph
(subgraph needs the glasgow submodule we don't build) and the rpack extern.

Copied into external/minorminer-fork/ by scripts/build_mm_fork.sh, then run:
    python setup_mmfork.py build_ext --inplace

Produces minorminer/_minorminer*.so, importable standalone (it only imports
os/logging at the Python level), so it loads next to a stock minorminer install.
"""
import platform
from setuptools import setup, Extension
from Cython.Build import cythonize

if platform.system().lower() == "windows":
    args = ['/std:c++17', '/MT', '/EHsc']
else:
    args = ['-std=c++17', '-Wall', '-Wno-format-security', '-Ofast',
            '-fomit-frame-pointer', '-g1', '-fno-rtti']

ext = Extension(
    name="minorminer._minorminer",
    sources=["./minorminer/_minorminer.pyx"],
    include_dirs=['', './include/', './include/find_embedding'],
    language='c++',
    extra_compile_args=args,
)

setup(
    name="minorminer-fork-ext",
    ext_modules=cythonize([ext], language_level=2),
    packages=[],            # disable setuptools flat-layout auto-discovery
    py_modules=[],
    script_args=["build_ext", "--inplace"],
)
