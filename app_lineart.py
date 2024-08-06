import websocket
import uuid
import json
import urllib.request
import urllib.parse
import gradio as gr
from PIL import Image
import io

server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_images(ws, prompt):
    prompt_id = queue_prompt(prompt)['prompt_id']
    output_images = {}
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break # Execution is done
        else:
            continue # previews are binary data

    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
            output_images[node_id] = images_output

    return output_images

with open("workflow_lineart_api.json" , 'r' , encoding="utf-8") as f:
    workflow_jsondata = f.read()

jsonwf = json.loads(workflow_jsondata)

def generate_image(user_input):
    prompt_text = f"a lineart themed drawing of a ({user_input}) consisting of simple and thin single lines"
    jsonwf["6"]["inputs"]["text"] = prompt_text

    jsonwf["3"]["inputs"]["seed"] = 737737

    ws = websocket.WebSocket()
    ws.connect(f"ws://{server_address}/ws?clientId={client_id}")
    images = get_images(ws, jsonwf)

    image_outputs = []
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            image_outputs.append(image)
    
    return image_outputs[0] if image_outputs else None

input_text = gr.Textbox(label="Enter an object for the prompt")
output_image = gr.Image(type="pil", label="Generated Image")

gr.Interface(fn=generate_image, inputs=input_text, outputs=output_image, title="Flat VectorArt Generator").launch(share=True)
