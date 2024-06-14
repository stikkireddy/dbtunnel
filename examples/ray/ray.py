# Databricks notebook source
# MAGIC %pip install dbtunnel[ray] transformers 
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

ngrok_api_key: str = dbutils.secrets.get("fieldeng", "ngrok-api-key")
ngrok_tunnel_auth_token: str = dbutils.secrets.get("fieldeng", "ngrok-tunnel-auth-token")

# COMMAND ----------

from ray import serve
from ray.serve.deployment import Application

from transformers import pipeline

@serve.deployment(num_replicas=2, )
class SentimentAnalysis:

  def __init__(self):
    self._classifier = pipeline("sentiment-analysis")

  def __call__(self, request) -> str:
    input_text: str = request.query_params["input_text"]
    return self._classifier(input_text)[0]["label"]
  
  
app: Application = SentimentAnalysis.bind() #noqa: F821
 
  

# COMMAND ----------

from dbtunnel import dbtunnel

(
  dbtunnel.ray(app, port=8080)
    .inject_auth()
    .share_to_internet_via_ngrok(
        ngrok_api_token=ngrok_api_key, 
        ngrok_tunnel_auth_token=ngrok_tunnel_auth_token)
    .run()
)
