# Databricks notebook source
!pip install dbtunnel[asgiproxy,chainlit] databricks-genai-inference langchain-community tiktoken langchain mlflow-skinny chromadb rank_bm25 simsimd

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/chainlit_foundation_model.py"

# COMMAND ----------

from dbtunnel import dbtunnel

dbtunnel.chainlit(script_path, port=8988).inject_auth().run()

# COMMAND ----------


