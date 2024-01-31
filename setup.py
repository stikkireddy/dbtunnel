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
    install_requires=[],
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    # TODO: start refactoring nest_asyncio only when async.run is needed
    extras_require={
        "fastapi": [
            # Specify dependencies for building documentation here
            "fastapi",
            "uvicorn",
            "nest_asyncio",
        ],
        "streamlit": [
            # Specify dependencies for building documentation here
            "streamlit",
            "pyarrow>=11",
            "nest_asyncio",
        ],
        "gradio": [
            # Specify dependencies for building documentation here
            "gradio==3.50.2",
            "nest_asyncio",
        ],
        "nicegui": [
            # Specify dependencies for building documentation here
            "nicegui",
            "nest_asyncio",
        ],
        "bokeh": [
            "bokeh",
            "nest_asyncio",
        ],
        "flask": [
            "flask",
            "fastapi",
            "uvicorn", # no websockets
            "nest_asyncio",
        ],
        "dash": [
            "dash",
            "fastapi",
            "uvicorn", # no websockets
            "nest_asyncio",
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
            "nest_asyncio",
            "uvicorn",
        ],
        "asgiproxy": [
            "aiohttp",
            "starlette",
            "uvicorn",
            "websockets",
            "python-multipart"  # we are using this for auth check via form uploads
        ],
        "shiny": [
            "shiny",
            "nest_asyncio",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
