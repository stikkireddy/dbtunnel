# Databricks notebook source
# MAGIC %pip install dbtunnel[asgiproxy,chainlit]

# COMMAND ----------

# MAGIC %pip install databricks-genai-inference langchain-community tiktoken langchain mlflow-skinny chromadb rank_bm25 simsimd

# COMMAND ----------

# MAGIC %pip install -U langchain==0.1.3 aiohttp sqlalchemy

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### RAG Demo using Foundation Model APIs (Mixtral 8x7b Instruct Chat + BGE-en-Large Embeddings)
# MAGIC
# MAGIC Take a look at the langchain code in the file `chainlit_foundation_model.py`.

# COMMAND ----------

import os

current_directory = os.getcwd()
script_path = current_directory + "/chainlit_foundation_model.py"

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.chainlit(script_path).inject_auth().run()

# COMMAND ----------


