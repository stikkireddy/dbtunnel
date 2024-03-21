# Gradio Integration in dbtunnel

## Description
Gradio allows you to create easy-to-use ML demos, UIs for Python scripts, and more. The dbtunnel integration with Gradio enables you to run these interfaces in the context of dbtunnel, facilitating seamless interaction with your data and models.

## Basic Usage

### Installation
To use Gradio within dbtunnel, first install the dbtunnel package with Gradio support:

```
%pip install dbtunnel[gradio]
dbutils.library.restartPython()
```

### Gradio Specific Code

To create a Gradio interface, define your functions and set up the Gradio blocks as follows:

```python
import gradio as gr

def combine(a, b):
    return a + " " + b

def mirror(x):
    return x

with gr.Blocks() as demo:
    txt = gr.Textbox(label="Input", lines=2)
    txt_2 = gr.Textbox(label="Input 2")
    txt_3 = gr.Textbox(value="", label="Output")
    btn = gr.Button(value="Submit")
    btn.click(combine, inputs=[txt, txt_2], outputs=[txt_3])

    with gr.Row():
        im = gr.Image()
        im_2 = gr.Image()

    btn = gr.Button(value="Mirror Image")
    btn.click(mirror, inputs=[im], outputs=[im_2])

    gr.Markdown("## Text Examples")
    gr.Examples([["hi", "Adam"], ["hello", "Eve"]], [txt, txt_2], txt_3, combine, cache_examples=True)
```

### Run your app

Integrate the Gradio app with dbtunnel and run it as follows in another cell:

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(demo).run() # demo is the name of the interface we have
```

This setup allows you to create interactive demos for your projects within the dbtunnel framework, 
leveraging Gradio's intuitive UI components.

## Advanced File based Usage with Gradio

Lets take a look at decoupling gradio code from the driver notebook to run. 
We can use the same demo as above, lets create a file called gradio_example.py

```python title="gradio_example.py"
--8<-- "examples/gradio/gradio_example.py"
```

Then in the driver notebook we can run the following to retrieve the current path to the gradio file:

```python
import os

current_directory = os.getcwd()
script_path = current_directory + "/gradio_example.py"
if os.path.exists(script_path) is False:
  raise Exception(f"File doesnt exist: {script_path}") 
```

`script_path` contains the path to the gradio file and we can pass that to dbtunnel to 
run that in a separate process using uvicorn. 

```python
from dbtunnel import dbtunnel
dbtunnel.gradio(path=script_path).run()
```

Then you should get a link to the app:

```
[2024-01-31T17:46:53+0000] [INFO] {gradio.py:_run:99} - Use this link to access the Gradio UI in Databricks: 
https://dbc-dp-.....cloud.databricks.com/driver-proxy/o/...../..../.../
```
