from setuptools import setup

setup(
    name="pfg-retirement",
    version="0.2.9",
    packages=['pfg'],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "docutils>=0.3",
        "numpy==1.19.2",
        "pandas==1.1.2",
        "selenium==3.141.0",
        "BeautifulSoup4",
    ],

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": ["*.txt", "*.rst"],
        # And include any *.msg files found in the "hello" package, too:
        "hello": ["*.msg"],
    },

    # metadata to display on PyPI
    author="Adam Lathan",
    author_email='',
    description="First pass of PFG api",
    url="https://github.com/lathaniel/pfg-retirement"
)
