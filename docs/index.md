---
hide:
  - navigation
---

# DBTunnel

Proxy solution to run elegant Web UIs natively inside databricks notebooks.

## Purpose

DBTunnel is a feature that helps you with very little code take a script in various 
frameworks and host it on a databricks cluster in a secure fashion. It supports common 
frameworks like gradio, chainlit, fastapi, shiny-python, solara, streamlit, etc. The goal
of DBTunnel is that you will not have any "DBTunnel" code or logic in your actual app. It is 
separate driver notebook that you can use to properly wire your app in a Databricks Cluster.

## Framework Support / Roadmap

- [x] [FastAPI](https://fastapi.tiangolo.com/){:target="_blank"}
- [x] [Gradio](https://gradio.app/){:target="_blank"}
- [x] [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui){:target="_blank"}
- [x] [Streamlit](https://streamlit.io/){:target="_blank"}
- [ ] [NiceGUI](https://nicegui.io/){:target="_blank"}
- [x] [Flask](https://palletsprojects.com/p/flask/){:target="_blank"}
- [x] [Dash](https://plotly.com/dash/){:target="_blank"}
- [x] [Bokeh](https://bokeh.org/){:target="_blank"}
- [x] [Shiny for Python](https://shiny.posit.co/py/){:target="_blank"}
- [ ] [Panel](https://panel.holoviz.org/){:target="_blank"}
- [x] [Solara](https://solara.dev/){:target="_blank"}
- [x] [ChainLit](https://chainlit.io/){:target="_blank"}
- [x] [code-server](https://coder.com/docs/code-server/latest){:target="_blank"}


There are various examples for you to try out!


## Disclaimer
dbtunnel is not developed, endorsed not supported by Databricks. It is provided as-is; no warranty is derived from using this package. 
For more details, please refer to the license.