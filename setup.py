from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="classic-models-seeder",
    version="0.1.0",
    author="Classic Models Team",
    description="CLI tool for seeding applications with Classic Models demo data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jiridj/classic-models-seeder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "tenacity>=8.2.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cmcli=cmcli.cli:cli",
        ],
    },
)

# Made with Bob
