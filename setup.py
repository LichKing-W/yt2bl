from setuptools import setup, find_packages

setup(
    name="youtube-to-bilibili",
    version="0.1.0",
    description="YouTube to Bilibili video transfer tool for computer science content",
    packages=find_packages(),
    python_requires=">=3.13",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
        "pydantic>=2.5.0",
        "rich>=13.7.0",
        "click>=8.1.0",
        "tqdm>=4.66.0",
        "yt-dlp>=2023.12.30",
    ],
    extras_require={
        "video": ["moviepy>=1.0.3"],
        "bilibili": ["bilibili-api-python>=13.1.0"],
        "dev": ["ruff>=0.1.0", "pytest>=7.4.0", "pytest-asyncio>=0.21.0", "black>=23.0.0", "mypy>=1.7.0"],
    },
    entry_points={
        "console_scripts": [
            "yt2bl=src.main:cli",
        ],
    },
)
