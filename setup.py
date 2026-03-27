from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Try to read VERSION file, fallback to default if not found
try:
    with open("VERSION", "r", encoding="utf-8") as fh:
        version = fh.read().strip()
except FileNotFoundError:
    version = "0.0.1"

setup(
    name="refactoring",
    version=version,
    author="Your Name",
    author_email="your.email@example.com",
    description="A package for code analysis and refactoring tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/refactoring",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "ast-tools>=0.1.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "refactor=refactoring.cli:main",
        ],
    },
)
