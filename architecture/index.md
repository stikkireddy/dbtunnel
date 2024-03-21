---
hide:
  - navigation
---


# Architecture

Here is a high level architecture diagram of a user's request going through the
process of retrieving data. This is not the situation with all apps but this is very feasible.

Keep in mind that the code of DBTunnel is the yellow bit of the diagram. The rest is the user's code. 
The proxy intercepts the requests and rewrites the html and js files to allow for the app to be hosted behind a proxy 
as needed. The reason for doing this is a lot of these apps are not designed to run/sit behind proxies. They expect
to be served at the root of the domain. And they send pre-rendered HTML that does not take into the location of the browser
window location. DBTunnel proxy rewrites are a stop gap.

Traffic flows through in the following order:

1. The user's browser
2. The Databricks Driver Proxy URL
3. The Driver Proxy
4. The DBTunnel Proxy (for most frameworks)
   1. The DBTunnel ASGI proxy handles http requests and websocket requests separately 
5. The User's App (gradio, chainlit, etc.)
6. [Optional] DBSQL connector/mlflow deployment client/requests library
7. [Optional] DBSQL Warehouse / Model serving endpoint / Jobs / etc.
8. [Optional] Unity Catalog / Databricks Clusters / etc.

<br>

![Image title](./imgs/DBTunnel%20Arch.png)

