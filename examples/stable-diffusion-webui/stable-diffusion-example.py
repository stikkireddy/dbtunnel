# Databricks notebook source
# MAGIC %pip install "git+https://github.com/stikkireddy/dbtunnel.git"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.stable_diffusion_ui(no_gpu=True).run()
