from setuptools import setup, find_packages
from pathlib import Path

README = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="mlops-dev",
    version="0.7.0",
    description="Deploy, monitor, and manage ML models on edge devices at scale",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://www.mlops.dev",
    project_urls={
        "Documentation": "https://docs.mlops.dev/api",
        "Source":        "https://github.com/Raghunath2604/Raghunath2604-mlops-dev",
        "Tracker":       "https://github.com/Raghunath2604/Raghunath2604-mlops-dev/issues",
        "Discord":       "https://discord.gg/Tb47N9NaPk",
        "Roadmap":       "https://roadmap.mlops.dev",
        "PyPI":          "https://pypi.org/project/mlops-dev",
    },
    author="Raghunathareddy GR",
    author_email="hello@mlops.dev",
    license="Apache-2.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Systems Administration",
        "Environment :: Console",
        "Operating System :: POSIX :: Linux",
    ],
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "full": [
            "requests>=2.28.0",
            "rich>=13.0.0",     # pretty CLI tables
        ],
        "dev": [
            "pytest>=7.0.0",
            "responses>=0.23.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mlops=mlops_dev.cli:main",
        ],
    },
    keywords=[
        "mlops", "edge-ai", "edge-ml", "machine-learning",
        "deployment", "inference", "jetson", "raspberry-pi",
        "onnx", "tflite", "tensorrt", "drift-detection",
        "canary", "fleet-management",
    ],
)
