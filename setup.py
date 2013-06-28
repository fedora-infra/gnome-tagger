#!/usr/bin/env python

"""
Setup script
"""

from setuptools import setup
from gnometagger.tagger import __version__

setup(
    name = 'gnome-tagger',
    description = 'Gnome-tagger is a desktop application for the web fedora-tagger application.',
    version = __version__,
    author = 'Pierre-Yves Chibon',
    author_email = 'pingou@pingoured.fr',
    maintainer = 'Pierre-Yves Chibon',
    maintainer_email = 'pingou@pingoured.fr',
    license = 'GPLv2+',
	url = 'https://github.com/fedora-infra/gnome-tagger',
    packages=['gnometagger'],
    include_package_data=True,
    install_requires=['requests'],
    entry_points="""
    [console_scripts]
    gnome-tagger = gnometagger.tagger:main
    """,
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        ],

    )
