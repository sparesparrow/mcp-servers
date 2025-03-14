from setuptools import setup, find_packages

setup(
    name="mcp-xpra-server",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "mcp>=1.0.0",
        "anthropic>=0.3.0",
        "python-dotenv>=0.19.0",
        "psutil>=5.9.0",
        "pyyaml>=6.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "ruff>=0.0.2",
            "mypy>=1.0.0",
            "pytest-cov>=4.0.0"
        ]
    },
    entry_points={
        'console_scripts': [
            'mcp-xpra=mcp_xpra_server.__main__:main',
        ],
    },
)
