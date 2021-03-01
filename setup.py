import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()
print(setuptools.find_packages())

setuptools.setup(
    name="pyhtmlgui",
    version="1.1",
    author="Dirk Makerhafen",
    author_email="dirk@makerhafen.de",
    description="A Python library for building user interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dirk-attraktor/pyHtmlGui",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    package_data={'pyhtmlgui': ['assets/electron/*', 'assets/templates/*']},
    #include_package_data=True,
)
