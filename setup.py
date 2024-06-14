from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dbtunnel",
    author="Sri Tikkireddy",
    author_email="sri.tikkireddy@databricks.com",
    description="Run app and get cluster proxy url for it in databricks clusters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    package_data={
        'dbtunnel': ['**/*.html'],
    },
    url="https://github.com/stikkireddy/dbtunnel",
    packages=find_packages(),
    install_requires=["nest_asyncio", "databricks-sdk>=0.18.0"],
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    # TODO: start refactoring nest_asyncio only when async.run is needed
    extras_require={
        "fastapi": [
            # Specify dependencies for building documentation here
            "fastapi",
            "uvicorn",
        ],
        "uvicorn": [
            # Specify dependencies for building documentation here
            "uvicorn",
        ],
        "streamlit": [
            # Specify dependencies for building documentation here
            "streamlit",
            "pyarrow>=11",
        ],
        "gradio": [
            # Specify dependencies for building documentation here
            "gradio==3.50.2",
        ],
        "nicegui": [
            # Specify dependencies for building documentation here
            "nicegui",
        ],
        "bokeh": [
            "bokeh",
        ],
        "flask": [
            "flask",
            "fastapi",
            "uvicorn",  # no websockets
        ],
        "dash": [
            "dash",
            "fastapi",
            "uvicorn",  # no websockets
        ],
        "sql": [
            "databricks-sql-connector"
        ],
        "solara": [
            "solara",
        ],
        "ngrok": [
            # going back to pyngrok its more stable and easy to delete sessions
            "pyngrok",
            "ngrok-api",
            "requests",
        ],
        "chainlit": [
            "chainlit",
            "uvicorn",
        ],
        "asgiproxy": [
            "aiohttp",
            "starlette",
            "uvicorn",
            "websockets",
            "python-multipart",  # we are using this for auth check via form uploads
            "cachetools"
        ],
        "shiny": [
            "shiny",
        ],
        "dev": [
            "mkdocs-material",
            "mkdocs-jupyter",
        ],
        "cli": [
            "click",
        ],
        "arize-phoenix": [
            "arize-phoenix"
        ],
        "ray": [
            "ray",
            "fastapi",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'dbtunnel = dbtunnel.cli.cli:cli',
        ],
    },
    python_requires=">=3.10",
)
