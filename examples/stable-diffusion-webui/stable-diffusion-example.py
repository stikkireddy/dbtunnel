# Databricks notebook source
# MAGIC %pip install dbtunnel

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.stable_diffusion_ui(no_gpu=True).run()
