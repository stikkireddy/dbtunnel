# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,streamlit]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/streamlit_example.py"

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.streamlit(script_path).run()

# COMMAND ----------


