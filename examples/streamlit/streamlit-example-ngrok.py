# Databricks notebook source
# MAGIC %pip install dbtunnel[streamlit,ngrok]

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
dbtunnel.streamlit(script_path).share(<ngrok-token>).run()

# COMMAND ----------


