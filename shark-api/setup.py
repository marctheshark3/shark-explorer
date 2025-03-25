from setuptools import setup, find_packages

setup(
    name="shark-api",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.95.0,<0.96.0",
        "uvicorn>=0.22.0,<0.23.0",
        "pydantic>=1.10.0,<2.0.0",
        "sqlalchemy>=2.0.0,<3.0.0",
        "asyncpg>=0.27.0,<0.28.0",
        "prometheus-client>=0.17.0,<0.18.0",
        "psycopg>=3.1.8,<4.0.0",
        "aiohttp>=3.8.4,<3.9.0",
        "structlog>=21.1.0",
        "python-dotenv>=0.19.0",
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