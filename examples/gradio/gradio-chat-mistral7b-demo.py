# Databricks notebook source
# MAGIC %md
# MAGIC # Serving Mistral-7B-Instruct via vllm with a cluster driver proxy app
# MAGIC
# MAGIC The [Mistral-7B-Instruct-v0.1](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1) Large Language Model (LLM) is a instruct fine-tuned version of the [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) generative text model using a variety of publicly available conversation datasets.
# MAGIC [vllm](https://github.com/vllm-project/vllm/tree/main) is an open-source library that makes LLM inference fast with various optimizations.
# MAGIC
# MAGIC Environment for this notebook:
# MAGIC - Runtime: 14.0 GPU ML Runtime
# MAGIC - Instance: `g5.xlarge` on AWS, `Standard_NV36ads_A10_v5` on Azure
# MAGIC

# COMMAND ----------

# MAGIC %pip install dbtunnel[gradio] vllm==0.2.0 transformers==4.34.0 accelerate==0.20.3

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inference
# MAGIC The example in the model card should also work on Databricks with the same environment.
# MAGIC

# COMMAND ----------

from vllm import LLM

# it is suggested to pin the revision commit hash and not change it for reproducibility because the uploader might change the model afterwards; you can find the commmit history of Mistral-7B-Instruct-v0. in https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1/commits/main
model = "mistralai/Mistral-7B-Instruct-v0.1"
revision = "3dc28cf29d2edd31a0a7b8f0b21637059815b4d5"

llm = LLM(model=model, revision=revision)

# COMMAND ----------

from vllm import SamplingParams

# Prompt templates as follows could guide the model to follow instructions and respond to the input, and empirically it turns out to make Falcon models produce better responses
DEFAULT_SYSTEM_PROMPT = """\
You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.

If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."""

INTRO_BLURB = "Below is an instruction that describes a task. Write a response that appropriately completes the request."
PROMPT_FOR_GENERATION_FORMAT = """
<s>[INST]<<SYS>>
{system_prompt}
<</SYS>>


{instruction}
[/INST]
""".format(
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    instruction="{instruction}"
)

# Define parameters to generate text
def gen_text_for_serving(prompt, **kwargs):
    prompt = PROMPT_FOR_GENERATION_FORMAT.format(instruction=prompt)

    # the default max length is pretty small (20), which would cut the generated output in the middle, so it's necessary to increase the threshold to the complete response
    if "max_tokens" not in kwargs:
        kwargs["max_tokens"] = 512

    sampling_params = SamplingParams(**kwargs)

    outputs = llm.generate(prompt, sampling_params=sampling_params)
    texts = [out.outputs[0].text for out in outputs]

    return texts[0]


# COMMAND ----------

print(gen_text_for_serving("How to master Python in 3 days?"))

# COMMAND ----------

import gradio as gr
import time

def respond(message, history):
    computed_gen = str(gen_text_for_serving(message))
    for i in range(len(computed_gen)):
          time.sleep(0.05)
          yield computed_gen[: i+1]
    return 

demo = gr.ChatInterface(fn=respond, examples=["hello what is the python language?"], title="Mistral Bot").queue()

# COMMAND ----------

from dbtunnel import dbtunnel
dbtunnel.gradio(demo).run()

# COMMAND ----------


