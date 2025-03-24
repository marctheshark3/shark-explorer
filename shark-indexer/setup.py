from setuptools import setup, find_packages

setup(
    name="shark-indexer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "asyncpg>=0.29.0",
        "aiohttp>=3.9.1",
        "pydantic>=2.5.2",
        "python-dotenv>=1.0.0",
        "alembic>=1.13.0",
        "prometheus-client>=0.19.0",
        "structlog>=24.1.0",
        "sqlalchemy>=2.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.23.2",
            "httpx>=0.25.2",
            "black>=23.11.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
        ]
    },
    entry_points={
        "console_scripts": [
            "shark-indexer=shark_indexer.__main__:main",
        ]
    },
) 