# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,gradio]

# COMMAND ----------

# MAGIC %pip install -U gradio==4.16.0

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/gradio_example.py"
if os.path.exists(script_path) is False:
  raise Exception(f"File doesnt exist: {script_path}") 

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.gradio(path=script_path).run()

# COMMAND ----------


