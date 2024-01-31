# Databricks notebook source
# MAGIC %pip install dbtunnel[gradio]

# COMMAND ----------

# MAGIC %pip install -U databricks-sdk databricks-sql-connector

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Get the first serverless warehouse

# COMMAND ----------

from dbtunnel import ctx, compute_utils

# defaults to serverless only and ignores case
# just run the first warehouse
details = compute_utils.get_warehouse("*", ignore_case=True, serverless_only=True)
if details is None:
  raise Exception("Unable to find a cluster with the following setting")
hostname, path = details.hostname, details.http_path
# printing the name dont really need it anywhere else
hostname, path, details.name

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Setup

# COMMAND ----------

from databricks import sql
import os

CATALOG = "main"
SCHEMA = "default"

with sql.connect(server_hostname = hostname,
                 http_path       = path,
                 access_token    = ctx.token) as connection:
  with connection.cursor() as cursor:
    cursor.execute(f"""CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.trips_example AS
SELECT * FROM samples.nyctaxi.trips LIMIT 100;""")
  with connection.cursor() as cursor:
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.trips_feedback (
  email STRING,
  feedback STRING,
  datetime STRING
) USING DELTA;""")


# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## Handler functions

# COMMAND ----------

import pandas as pd
def get_trips_df(token):
  with sql.connect(server_hostname = hostname,
                 http_path       = path,
                 access_token    = token) as connection:
    with connection.cursor() as cursor:
      cursor.execute(f"SELECT * FROM {CATALOG}.{SCHEMA}.trips_example")
      # Fetch the result
      result = cursor.fetchall()

      # Convert the result to a DataFrame
      columns = [column[0] for column in cursor.description]
      return pd.DataFrame(result, columns=columns)

def get_feedback_df(token):
  with sql.connect(server_hostname = hostname,
                 http_path       = path,
                 access_token    = token) as connection:
    with connection.cursor() as cursor:
      cursor.execute(f"SELECT * FROM {CATALOG}.{SCHEMA}.trips_feedback")
      # Fetch the result
      result = cursor.fetchall()

      # Convert the result to a DataFrame
      columns = [column[0] for column in cursor.description]
      return pd.DataFrame(result, columns=columns)
    
from datetime import datetime
def insert_feedback(email: str, feedback: str, token: str):
  with sql.connect(server_hostname = hostname,
                 http_path       = path,
                 access_token    = token) as connection:
    with connection.cursor() as cursor:
      cursor.execute(f"INSERT INTO {CATALOG}.{SCHEMA}.trips_feedback VALUES (?, ?, ?)", (email, feedback, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


# COMMAND ----------

import gradio as gr
import pandas as pd
from databricks.sdk import WorkspaceClient
import os

def get_current_user(token: str):
  if token is None:
    return None
  try:
      # based on user's input token
      return WorkspaceClient(host=ctx.host,token=token).current_user.me().user_name
  except Exception as e:
      print(e)
      return None

def submit(token: str):
    user = get_current_user(token)
    if user is None:
      return None, None, "Invalid Token"
    return get_trips_df(token), get_feedback_df(token), user


def insert_review(feedback: str, token: str):
  insert_feedback(get_current_user(token), feedback, token)
  return get_feedback_df(token)


with gr.Blocks() as demo:

    token_field = gr.Textbox(label="Token", type="password", lines=1)
    workspace = gr.Textbox(label="Workspace", value=ctx.host, lines=1)
    logged_in_as = gr.Textbox(label="Email", lines=1)
    with gr.Row():
      data = gr.DataFrame(label="Raw Data")
      feedback_display = gr.DataFrame(label="Feedback Data")
    btn = gr.Button(value="Submit")
    btn.click(submit, inputs=[token_field], outputs=[data, feedback_display, logged_in_as])

    with gr.Row():
        feedback = gr.Textbox(label="Feedback")
    
    feedback_btn = gr.Button(value="Submit Feedback")
    feedback_btn.click(insert_review, inputs=[feedback, token_field], outputs=[feedback_display])


# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.gradio(demo).run()

# COMMAND ----------


