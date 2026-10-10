from pathlib import Path

import setuptools

VERSION = "0.0.3"

NAME = "satypy"

INSTALL_REQUIRES = [
    "networkx[default]>=3.4.2",
    "salvador==0.1.0",
    "python-sat",
]

setuptools.setup(
    name=NAME,
    version=VERSION,
    description="Solve the Boolean Satisfiability (SAT) problem using a DIMACS file as input.",
    url="https://github.com/frankvegadelgado/satypy",
    project_urls={
        "Source Code": "https://github.com/frankvegadelgado/satypy",
        "Documentation Research": "https://github.com/frankvegadelgado/satypy",
    },
    author="Frank Vega",
    author_email="vega.frank@gmail.com",
    license="MIT License",
    classifiers=[
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
    ],
    python_requires=">=3.12",
    # Requirements
    install_requires=INSTALL_REQUIRES,
    packages=["satypy"],
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': [
            'saty = satypy.app:main',
            'batch_saty = satypy.batch:main',
            'test_saty = satypy.test:main'
        ]
    }
)