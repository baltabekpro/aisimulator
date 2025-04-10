from setuptools import setup, find_packages

setup(
    name="aisimulatorbot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "pydantic-settings",  # Add pydantic-settings explicitly
        "python-jose[cryptography]",
        "python-multipart",
        "passlib[bcrypt]",
        "python-dotenv",
        "psycopg2-binary",
        "alembic",
        "pyjwt",
        "requests",
    ],
)