import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyhtmlgui",
    version="3.22",
    author="Dirk Makerhafen",
    author_email="dirk@makerhafen.de",
    description="A Python library for building user interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dirk-makerhafen/pyHtmlGui",
    packages=setuptools.find_namespace_packages(),
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    package_data={'pyhtmlgui': ['assets/electron/*', 'assets/templates/*']},
    include_package_data=True,
)
