import runpod
import json
import urllib.request
import urllib.parse
import uuid
import base64
import websocket

SERVER_ADDRESS = "127.0.0.1:8188"

def queue_prompt(prompt, prompt_id):
    p = {"prompt": prompt, "client_id": str(uuid.uuid4()), "prompt_id": prompt_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data,
                                 headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req).read()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def execute_workflow(workflow):
    prompt_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    queue_prompt(workflow, prompt_id)
    
    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={client_id}")
    
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                if message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                    break
    ws.close()
    
    history = get_history(prompt_id)[prompt_id]
    output_images = []
    
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'images' in node_output:
            for image_info in node_output['images']:
                image_data = get_image(image_info['filename'], image_info['subfolder'], image_info['type'])
                b64_data = base64.b64encode(image_data).decode('utf-8')
                output_images.append(f"data:image/png;base64,{b64_data}")
    
    return output_images

def handler(job):
    job_input = job["input"]
    workflow = job_input.get("workflow")
    
    if not workflow:
        return {"error": "Missing 'workflow' in input"}
    
    try:
        images = execute_workflow(workflow)
        return {"images": images, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

if __name__ == '__main__':
    runpod.serverless.start({"handler": handler})
