from setuptools import setup, find_packages

setup(
    name="py-doc2docx",
    version="0.1.0",
    description="Convert Markdown Technical Documentation to Word (.docx) Documents",
    author="Mark Bacon",
    packages=find_packages(),
    install_requires=[
        "python-docx>=1.0.0",
        "colorlog>=6.7.0"
    ],
    entry_points={
        "console_scripts": [
            "py-doc2docx=pydoc2docx.cli:main",
        ],
    },
    python_requires=">=3.9",
)
