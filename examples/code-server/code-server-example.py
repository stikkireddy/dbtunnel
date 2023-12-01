# Databricks notebook source
# MAGIC %pip install dbtunnel

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from dbtunnel import dbtunnel
# alternatively you can do directory_path= for full directory
# dbtunnel.code_server(directory_path="/Workspace/...").run()
# no need for auth you should be using single user clusters!
dbtunnel.code_server(repo_name="dbtunnel").run()

# COMMAND ----------


