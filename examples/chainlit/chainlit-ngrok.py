# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,chainlit,ngrok]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/chainlit_example.py"

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.chainlit(script_path).share_to_internet_via_ngrok(
    ngrok_api_token="<ngrok api token>",
    ngrok_tunnel_auth_token="<ngrok tunnel auth token>"
).run()

# COMMAND ----------


