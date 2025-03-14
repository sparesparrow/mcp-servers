from setuptools import setup, find_packages

setup(
    name="mcp-prompt-manager",
    version="0.1.0",
    description="MCP server for managing reusable prompt templates",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Claude User",
    author_email="user@example.com",
    url="https://github.com/yourusername/mcp-prompt-manager",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "mcp>=0.1.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "black",
            "isort",
            "flake8",
            "mypy",
        ],
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "mcp-prompt-manager=prompt_manager_server:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 