# dbtunnel 

Proxy solution to run elegant Web UIs natively inside databricks notebooks.

**YOU CAN ONLY USE THIS IN DATABRICKS NOTEBOOKS WITH A RUNNING CLUSTER**

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
* [x] code-server on repos

Easy way to test out llm chatbots; look in examples/gradio

**You must use A10 GPU instances or higher**

* [x] Mistral-7b
* [ ] Llama-2-7b
* [ ] mpt-7b
* [ ] Streaming support (vllm, etc.)




## Setup

**Please do not use this in production!!**

1. Clone this repo into databricks repos
2. Go to any of the examples to see how to use them
3. Enjoy your proxy experience :-) 
4. If you want to share the link ensure that the other user has permission to attach to your cluster.



## Disclaimer
dbtunnel is not developed, endorsed not supported by Databricks. It is provided as-is; no warranty is derived from using this package. For more details, please refer to the license.