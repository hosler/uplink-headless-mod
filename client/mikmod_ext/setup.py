from setuptools import setup, Extension

mikmod_ext = Extension(
    "mikmodplayer",
    sources=["mikmodplayer.c"],
    libraries=["mikmod"],
)

setup(
    name="mikmodplayer",
    version="1.0",
    description="Python wrapper for libmikmod tracker rendering",
    ext_modules=[mikmod_ext],
)
