# Databricks notebook source
# MAGIC %md
# MAGIC # Serving Databricks chat completion model
# MAGIC
# MAGIC Using [llama-2-70b-chat](https://docs.databricks.com/en/machine-learning/foundation-models/query-foundation-model-apis.html) chat in a gradio chat app.
# MAGIC
# MAGIC We’re excited to announce that Meta AI’s Llama 2 foundation chat models are available in the Databricks Marketplace for you to fine-tune and deploy on private model serving endpoints. The Databricks Marketplace is an open marketplace that enables you to share and exchange data assets, including datasets and notebooks, across clouds, regions, and platforms. Adding to the data assets already offered on Marketplace, this new listing provides instant access to Llama 2's chat-oriented large language models (LLM), from 7 to 70 billion parameters, as well as centralized governance and lineage tracking in the Unity Catalog. Each model is wrapped in MLflow to make it easy for you to use the MLflow Evaluation API in Databricks notebooks as well as to deploy with a single-click on our LLM-optimized GPU model serving endpoints. 
# MAGIC
# MAGIC https://www.databricks.com/blog/llama-2-foundation-models-available-databricks-lakehouse-ai

# COMMAND ----------

# MAGIC %pip install dbtunnel[gradio] databricks-genai-inference

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inference
# MAGIC The example in the model card should also work on Databricks with the same environment.
# MAGIC

# COMMAND ----------

from databricks_genai_inference import ChatSession

# change the system prompt

def make_chat_session():
    system_message = "You are a helpful assistant."
    max_tokens = 128
    return ChatSession(model="llama-2-70b-chat", system_message=system_message, max_tokens=max_tokens)

chat = make_chat_session()

# COMMAND ----------

import gradio as gr
import time


def respond(message, history):
    # global so we can reset it
    global chat

    if history == []:
        # reset chat history when user runs clear
        chat = make_chat_session()

    chat.reply(message)
    computed_gen = str(chat.last)
    for i in range(0, len(computed_gen), 8):
        time.sleep(0.05)
        yield computed_gen[: i + 8]
    return 

demo = gr.ChatInterface(fn=respond, 
                        examples=["hello what is the python language?"], 
                        undo_btn=None,
                        retry_btn=None,
                        title="Llama 70b Foundational Model Chat Bot").queue()

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.gradio(demo).run()

# COMMAND ----------


