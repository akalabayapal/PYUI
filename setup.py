from setuptools import setup

# This trick forces setuptools to treat your package as a native binary platform distribution
setup(has_ext_modules=lambda: True)
