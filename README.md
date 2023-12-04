# dbtunnel 

Proxy solution to run elegant Web UIs natively inside databricks notebooks.

**YOU CAN ONLY USE THIS IN DATABRICKS NOTEBOOKS WITH A RUNNING CLUSTER**

**FOR SECURE ACCESS PLEASE USE A SINGLE USER CLUSTER (ANYONE WITH ATTACH CAN ACCESS THE UIs)** 

## Description

Easy way to test the following things on a databricks cluster and notebooks

### Framework Support

* [x] fastapi
* [x] gradio
* [x] stable diffusion webui
* [x] streamlit
* [x] nicegui
* [x] flask
* [x] dash
* [x] bokeh
* [ ] posit
* [ ] panel
* [x] solara
* [x] code-server on repos ([code-server-example.py](examples%2Fcode-server%2Fcode-server-example.py))

Easy way to test out llm chatbots; look in examples/gradio

### Chatbot Support

**You must use A10 GPU instances or higher**

* [x] Mistral-7b [gradio-chat-mistral7b-demo.py](examples%2Fgradio%2Fgradio-chat-mistral7b-demo.py)
* [ ] Llama-2-7b
* [ ] mpt-7b
* [ ] Streaming support (vllm, etc.)
* [x] Typewriter effect

### Tunnel Support:

* [x] ngrok
* [ ] devtunnels
* [ ] cloudflared



## Setup

**Please do not use this in production!!**

1. Clone this repo into databricks repos
2. Go to any of the examples to see how to use them
3. Enjoy your proxy experience :-) 
4. If you want to share the link ensure that the other user has permission to attach to your cluster.

## Exposing to internet using ngrok

**WARNING: IT WILL BE PUBLICLY AVAILABLE TO ANYONE WITH THE LINK SO DO NOT EXPOSE ANYTHING SENSITIVE**

The reason for doing this is to test something with a friend or colleague who is not logged in into databricks.
The proxy option requires you to be logged in into databricks.

1. Go to [ngrok](https://ngrok.com/) and create an account and get an api token
2. Go to a databricks notebook:
```python
from dbtunnel import dbtunnel

# again this example is with streamlit but works with any framework
dbtunnel.streamlit("<script path>").share("<ngrok-token>").run()
```



## Disclaimer
dbtunnel is not developed, endorsed not supported by Databricks. It is provided as-is; no warranty is derived from using this package. For more details, please refer to the license.