# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,streamlit,ngrok]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/streamlit_example.py"

# COMMAND ----------

from dbtunnel import dbtunnel

# Go to [ngrok](https://ngrok.com/) and create an account and get an api token
# get ngrok token from secrets or hardcode it
# you get ngrok tunnel auth token from here: https://dashboard.ngrok.com/get-started/your-authtoken
# you get the ngrok api token from here: https://dashboard.ngrok.com/api
# you must have both so that we can kill external sessions if this is a personal account
dbtunnel.streamlit(script_path).share_to_internet_via_ngrok(
    ngrok_api_token="<ngrok api token>",
    ngrok_tunnel_auth_token="<ngrok tunnel auth token>",
    # kill_all_tunnel_sessions=True,
).run()
