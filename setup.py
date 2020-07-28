import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyHtmlGui", # Replace with your own username
    version="0.2",
    author="Dirk Makerhafen",
    author_email="dirk@mex21.net",
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
    package_data={'pyHtmlGui': ['static/*']},
    include_package_data=True,

)
