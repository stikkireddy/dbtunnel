# Databricks notebook source
# MAGIC %pip install "git+https://github.com/stikkireddy/dbtunnel.git#egg=dbtunnel[flask]"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from flask import Flask

app = Flask("test")

@app.route('/')
def hello_world():
    return 'Hello, World!'


# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.flask(app).run()

# COMMAND ----------


