from setuptools import setup, find_packages

setup(
    name="shark-api",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "sqlalchemy>=1.4.0",
        "asyncpg>=0.24.0",
        "pydantic>=1.8.0",
        "pydantic-settings>=2.0.0",
        "structlog>=21.1.0",
        "python-dotenv>=0.19.0",
        "aiohttp>=3.8.0",
        "prometheus_client>=0.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.7b0",
            "isort>=5.9.0",
            "mypy>=0.910",
        ]
    },
    python_requires=">=3.9",
) 