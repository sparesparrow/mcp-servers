from setuptools import setup, find_packages

setup(
    name="mcp-xpra-server",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp",
        "anthropic",
        "python-dotenv"
    ],
    entry_points={
        'console_scripts': [
            'xpra-mcp=mcp_xpra_server:main',
        ],
    },
)