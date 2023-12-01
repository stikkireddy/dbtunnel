# dbtunnel 

Proxy solution to run elegant Web UIs natively inside databricks notebooks.

**YOU CAN ONLY USE THIS IN DATABRICKS NOTEBOOKS WITH A RUNNING CLUSTER**

**FOR SECURE ACCESS PLEASE USE A SINGLE USER CLUSTER (ANYONE WITH ATTACH CAN ACCESS THE UIs)** 

## Description

Easy way to test the following things on a databricks cluster and notebooks

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

**You must use A10 GPU instances or higher**

* [x] Mistral-7b [gradio-chat-mistral7b-demo.py](examples%2Fgradio%2Fgradio-chat-mistral7b-demo.py)
* [ ] Llama-2-7b
* [ ] mpt-7b
* [ ] Streaming support (vllm, etc.)
* [x] Typewriter effect




## Setup

**Please do not use this in production!!**

1. Clone this repo into databricks repos
2. Go to any of the examples to see how to use them
3. Enjoy your proxy experience :-) 
4. If you want to share the link ensure that the other user has permission to attach to your cluster.



## Disclaimer
dbtunnel is not developed, endorsed not supported by Databricks. It is provided as-is; no warranty is derived from using this package. For more details, please refer to the license.