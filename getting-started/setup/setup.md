# Setup

## 1: Requirements

You need access to a databricks workspace with the following things:

1. A single node cluster with "no isolation shared" mode and ability to download python packages from pypi
    1. You can optionally create a single user cluster but only you will be able to access the web ui
3. **[Optional]** Unity catalog access (to secure data, tables and ml models)
4. **[Optional]** Serverless SQL Warehouse (to securely access data in Unity Catalog)
5. **[Optional]** Users have the ability to make pat tokens (for user authentication)


## 2: Notebook Setup

The notebook will typically start with:

```python
%pip install dbtunnel[gradio,asgiproxy]
dbutils.library.restartPython()
```

The previous command installs the dbtunnel library along with the framework reqs. It also restarts python interpreter.

We will go into the various frameworks in more detail.

Once it is installed:

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(path="path/to/script/in/workspace.py").run()
```

There are additional arguments and options in dbtunnel to do various things.

## 3: Running the notebook

!!! warning

    Please do not use the url that starts with `0.0.0.0` or `localhost` or `10.x.x.x` as it will not work since thats local 
    inside the databricks driver. 


Once you run the notebook you will see a link to the web ui. 
You can share this link with anyone who has access to the databricks workspace who can attach to that cluster.

```
[2024-01-31T17:46:53+0000] [INFO] {gradio.py:_run:99} - Use this link to access the Gradio UI in Databricks: 
https://dbc-dp-.....cloud.databricks.com/driver-proxy/o/...../..../8080/
```