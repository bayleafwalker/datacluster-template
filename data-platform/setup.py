"""
Data Platform Setup

Install: pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="data-platform",
    version="0.1.0",
    description="Datacluster Common Data Pipeline Libraries",
    author="Data Platform Team",
    packages=find_packages(where=".", include=["common", "common.*"]),
    python_requires=">=3.9",
    install_requires=[
        "pyspark>=3.5.0",
        "delta-spark>=3.0.0",
        "confluent-kafka>=2.3.0",
        "boto3>=1.34.0",
        "avro-python3>=1.11.3",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-spark>=0.6.0",
            "black>=23.12.1",
            "mypy>=1.8.0",
        ],
        "quality": [
            "great-expectations>=0.18.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
