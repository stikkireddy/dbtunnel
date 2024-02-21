# dbtunnel 

Proxy solution to run elegant Web UIs natively inside databricks notebooks.

**YOU CAN ONLY USE THIS IN DATABRICKS NOTEBOOKS WITH A RUNNING CLUSTER**

**FOR SECURE ACCESS PLEASE USE A SINGLE USER CLUSTER (ANYONE WITH ATTACH CAN ACCESS THE UIs)** 

## Description

Easy way to test the following things on a databricks cluster and notebooks

### Framework Support

* [x] fastapi: [fastapi.py](examples%2Ffastapi%2Ffastapi.py)
* [x] gradio: [gradio-demo.py](examples%2Fgradio%2Fgradio-demo.py)
* [x] stable diffusion webui: [stable-diffusion-example.py](examples%2Fstable-diffusion-webui%2Fstable-diffusion-example.py)
* [x] streamlit: [streamlit_example.py](examples%2Fstreamlit%2Fstreamlit_example.py)
* [x] nicegui: [nicegui-example.py](examples%2Fnicegui%2Fnicegui-example.py)
* [x] flask: [flask-app.py](examples%2Fflask%2Fflask-app.py)
* [x] dash: [dask-example.py](examples%2Fdash%2Fdask-example.py)
* [x] bokeh: [bokeh-example.py](examples%2Fbokeh%2Fbokeh-example.py)
* [x] shiny for python: [shiny-python-example.py](examples%2Fshiny-python%2Fshiny-python-example.py)
* [ ] panel
* [x] solara: [solara-example.py](examples%2Fsolara%2Fsolara-example.py)
* [x] chainlit: [chainlit-foundation-model-rag-example.py](examples%2Fchainlit%2Fchainlit-foundation-model-rag-example.py)
* [x] code-server on repos [code-server-example.py](examples%2Fcode-server%2Fcode-server-example.py)

Easy way to test out llm chatbots; look in examples/gradio

### File or Directory Support

This is to support decoupling your UI code from your databricks notebooks. 
Usually will have a script_path argument instead of directly passing your "app" object. This is convenient for 
shipping your app outside of a notebook.

* [ ] fastapi: [fastapi.py](examples%2Ffastapi%2Ffastapi.py)
* [x] gradio: [gradio-demo.py](examples%2Fgradio%2Fgradio-demo.py)
* [x] streamlit: [streamlit_example.py](examples%2Fstreamlit%2Fstreamlit_example.py): This is partially implemented, it only works with one file. 
* [ ] nicegui: [nicegui-example.py](examples%2Fnicegui%2Fnicegui-example.py)
* [ ] flask: [flask-app.py](examples%2Fflask%2Fflask-app.py)
* [ ] dash: [dask-example.py](examples%2Fdash%2Fdask-example.py)
* [x] bokeh: [bokeh-example.py](examples%2Fbokeh%2Fbokeh-example.py)
* [ ] shiny for python
* [ ] panel
* [x] solara: [solara-example.py](examples%2Fsolara%2Fsolara-example.py)
* [x] chainlit: [chainlit-foundation-model-rag-example.py](examples%2Fchainlit%2Fchainlit-foundation-model-rag-example.py)

### Frameworks that leverage asgiproxy

DBTunnel provides a proxy layer using asgiproxy fork to support UIs that do not support proxy root paths, etc. It also
comes with a simple token based auth provider that only works on databricks to help you get access to user information.

DBTunnel Proxy features:
1. **Token based auth**: This is a simple token based auth that only works on databricks. 
This token is saved in the app memory as a python TTLCache object. 
2. **Support for frameworks that dont support proxies**: This proxy solution intercepts requests and rewrites js and html files 
to allow support for hosting behind proxies that are dynamic. This is a temporary measure before researching a way of 
exposing root path details. Then this step will be skipped. If you are running into issues with this please file a github issue.
3. **Support for audit logging**: This is simply logging tracked users and saving them to a file. Its yet to be implemented. 
4. **Support for frameworks that do not support root paths**
5. **Inject auth headers**: This is to provide user information directly to your app via request object. Most frameworks
support the access to request object to access headers, etc.

* [ ] fastapi
* [x] gradio
* [x] streamlit 
* [ ] nicegui
* [ ] flask
* [ ] dash
* [ ] bokeh
* [ ] shiny for python
* [ ] panel
* [ ] solara
* [x] chainlit


### Chatbot Support

**You must use A10 GPU instances or higher**

* [x] Mistral-7b [gradio-chat-mistral7b-demo.py](examples%2Fgradio%2Fgradio-chat-mistral7b-demo.py)
* [x] Mixtral 8x7B [chainlit-foundation-model.py](examples%2Fchainlit%2Fchainlit-foundation-model.py)
* [ ] Llama-2-7b
* [ ] mpt-7b
* [ ] Streaming support (vllm, etc.)
* [x] Streaming support foundation model api
* [x] Typewriter effect

### Tunnel Support:

* [x] ngrok
* [ ] devtunnels
* [ ] cloudflared
* [x] dbtunnel custom relay (private only)

## Setup

**Please do not use this in production!!**

1. Clone this repo into databricks repos
2. Go to any of the examples to see how to use them
3. Enjoy your proxy experience :-) 
4. If you want to share the link ensure that the other user has permission to attach to your cluster.

## Passing databricks auth to your app via `inject_auth`

You can pass databricks user auth from your notebook session to any of the frameworks by doing the following:

```python
from dbtunnel import dbtunnel
dbtunnel.<framework>(<script_path>).inject_auth().run()
```

For example: 

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(demo).inject_auth().run()
```

This exposes the user information via environment variable DATABRICKS_HOST and DATABRICKS_TOKEN.


## Passing a warehouse to your app via `inject_sql_warehouse`

You can pass databricks warehouse auth from your notebook session to any of the frameworks by doing the following:

```python
from dbtunnel import dbtunnel
dbtunnel.<framework>(<script_path>).inject_sql_warehouse().run()
```

This exposes the warehouse information via environment variable DATABRICKS_HOST, DATABRICKS_TOKEN and DATABRICKS_HTTP_PATH.


## Passing custom environment variables via `inject_env`

You can pass custom environment variables from your notebook to any of the frameworks by doing the following:

```python
from dbtunnel import dbtunnel
dbtunnel.<framework>(<script_path>).inject_env(**{
   "MY_CUSTOM_ENV": "my_custom_env_value"
}).run()
```

For example: 

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(demo).inject_env(**{
    "MY_CUSTOM_ENV": "my_custom_env_value"
}).run()
```

Alternatively

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(demo).inject_env(MY_CUSTOM_ENV="my_custom_env_value").run()
```

Keep in mind environment variables need to be keyword arguments!


## Exposing to internet using ngrok

**WARNING: IT WILL BE PUBLICLY AVAILABLE TO ANYONE WITH THE LINK SO DO NOT EXPOSE ANYTHING SENSITIVE**

The reason for doing this is to test something with a friend or colleague who is not logged in into databricks.
The proxy option requires you to be logged in into databricks.

1. Go to [ngrok](https://ngrok.com/) and create an account and get an api token and a tunnel auth token
    * You can get a tunnel token from [here](https://dashboard.ngrok.com/get-started/your-authtoken).
    * You can get an api token from [here](https://dashboard.ngrok.com/api).
2. Go to a databricks notebook:
3. **If you are using free tier of ngrok you can only have one tunnel and one session at a time so enable `kill_all_tunnel_sessions=True`** 

Take a look at the full example here [streamlit-example-ngrok.py](examples%2Fstreamlit%2Fstreamlit-example-ngrok.py)

```python
from dbtunnel import dbtunnel

# again this example is with streamlit but works with any framework
dbtunnel.streamlit("<script_path>").share_to_internet_via_ngrok(
    ngrok_api_token="<ngrok api token>",
    ngrok_tunnel_auth_token="<ngrok tunnel auth token>"
).run()

# if you need to kill tunnels because you are on free tier:
# again this example is with streamlit but works with any framework
dbtunnel.streamlit("<script_path>").share_to_internet_via_ngrok(
    ngrok_api_token="<ngrok api token>",
    ngrok_tunnel_auth_token="<ngrok tunnel auth token>",
    kill_all_tunnel_sessions=True,
).run()
```

## Killing processes on a specific port

```python
from dbtunnel import dbtunnel
dbtunnel.kill_port(<port number as int>)
```


## Disclaimer
dbtunnel is not developed, endorsed not supported by Databricks. It is provided as-is; no warranty is derived from using this package. For more details, please refer to the license.
