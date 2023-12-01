from setuptools import setup, find_packages

setup(
    name="dbtunnel",
    version="0.1.0",
    author="Sri Tikkireddy",
    author_email="sri.tikkireddy@databricks.com",
    description="Run app and get cluster proxy url for it in databricks clusters",
    long_description_content_type="text/markdown",
    url="https://github.com/stikkireddy/dbtunnel",
    packages=find_packages(),
    install_requires=[
        "nest_asyncio",
    ],
    extras_require={
        "fastapi": [
            # Specify dependencies for building documentation here
            "fastapi",
            "uvicorn",
        ],
        "streamlit": [
            # Specify dependencies for building documentation here
            "streamlit",
            "pyarrow>=11",
        ],
        "gradio": [
            # Specify dependencies for building documentation here
            "gradio",
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
        ],
        "dash": [
            "dash",
            "fastapi",
            "uvicorn" # no websockets
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
