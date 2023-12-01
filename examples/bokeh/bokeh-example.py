# Databricks notebook source
# MAGIC %pip install dbtunnel[bokeh]

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/bokeh_sample.py"

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.bokeh(script_path).run()
