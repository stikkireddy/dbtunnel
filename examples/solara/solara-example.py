# Databricks notebook source
# MAGIC %pip install dbtunnel[solara]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/scatter.py"

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.solara(script_path).run()
