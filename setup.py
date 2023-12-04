from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dbtunnel",
    version="0.5.0",
    author="Sri Tikkireddy",
    author_email="sri.tikkireddy@databricks.com",
    description="Run app and get cluster proxy url for it in databricks clusters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stikkireddy/dbtunnel",
    packages=find_packages(),
    install_requires=[
    ],
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
            "gradio",
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
            "pyngrok",
            "requests",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
