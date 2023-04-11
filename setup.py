import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pypkm",
    version="0.0.1",
    author="Adam Ferreira",
    author_email="adam.ferreira.dc@gmail.com",
    description="Pokemon",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adamferreira/pypkm",
    project_urls={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "pypkm"},
    packages=setuptools.find_packages(where="pypkm"),
    #packages = ["pypkm"], 
    package_data={
    # Install all csv scrapped data
        "data": ["scrapping/*/*.csv"]
    },
    test_suite="pypkm.tests",
    python_requires=">=3.0",
    install_requires=[
       "pandas"
   ],
)
