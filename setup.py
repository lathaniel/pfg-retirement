from setuptools import setup, find_packages

setup(
    name="pfg-retirement",
    version="0.1",
    packages=find_packages(),
    scripts=["pfg"],


    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=["docutils>=0.3"],

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": ["*.txt", "*.rst"],
        # And include any *.msg files found in the "hello" package, too:
        "hello": ["*.msg"],
    },

    # metadata to display on PyPI
    author="Adam Lathan",
    description="First pass of PFG api",
    project_urls={        
        "Source Code": "https://github.com/lathaniel/pfg-retirement/",
    },
    classifiers=[
        
    ]

    # could also include long_description, download_url, etc.
)