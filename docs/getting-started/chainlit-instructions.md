# Chainlit Integration in dbtunnel

## Description
Build production-ready Conversational AI applications in minutes, not weeks ⚡️.
This integration lets you run chainlit applications inside databricks clusters.


## Installation
To use Chainlit, you can install it along with the required dependencies using the following command:

```python
%pip install dbtunnel[asgiproxy,chainlit]
dbutils.library.restartPython()
```

## Driver Notebook Setup

To set up the driver notebook for Chainlit, follow these steps:

1. Get the current directory and specify the path to your Chainlit script file:

    ```python
    import os
    
    current_directory = os.getcwd()
    script_path = current_directory + "/chainlit_example.py"
    ```

2. Import the dbtunnel library and run the chainlit script

    ```python
    from dbtunnel import dbtunnel
    dbtunnel.chainlit(script_path).run()
    ```


## Chainlit Specific Code

In your Chainlit script (chainlit_example.py), you can define custom logic for your chainlit application. 
The provided code snippet is a basic example that responds to incoming messages:


```python title="chainlit_example.py"
import chainlit as cl

@cl.on_message
async def main(message: cl.Message):
    # Your custom logic goes here...

    # Send a response back to the user
    await cl.Message(
        content=f"Received: {message.content}",
    ).send()

```