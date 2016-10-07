import netTelD

NAME = 'netTelD'
VERSION = netTelD.VERSION
DESCRIPTION = "Python daemon which implements netTel"
LONG_DESCRIPTION = """
Python daemon which implements netTel as described in : https://docs.google.com/presentation/d/1uqVGDOPo5-3Nh-RG8vp5PKpKqlQo2ZMNAimxqwf6bs0/edit#slide=id.g1781e444bf_0_10
"""
AUTHOR = netTelD.AUTHOR
AUTHOR_EMAIL = netTelD.AUTHOR_EMAIL
LICENSE = "ASL 2.0"
PLATFORMS = "Any"
URL = ""
CLASSIFIERS = [
    "Development Status :: 2 - Pre-Alpha",
    "License :: OSI Approved :: Apache Software License",
    "Natural Language :: English",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Topic :: Scientific/Engineering :: Information Analysis",
    "Topic :: System :: Networking :: Monitoring"
]


from setuptools import setup

setup(name=NAME,
      version=VERSION,
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      platforms=PLATFORMS,
      url=URL,
      classifiers=CLASSIFIERS,
      keywords='operations python networking telemetry monitoring perfSonar',
      packages=['netTelD'],
      install_requires=[],
      data_files=[
          ('/usr/lib/systemd/system/', ['netTelD.service']),
      ]
      )