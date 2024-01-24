# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,chainlit]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/chainlit_example.py"

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.chainlit(script_path).run()

# COMMAND ----------


