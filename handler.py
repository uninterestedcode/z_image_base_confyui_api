import runpod
import time

def handler(job):
    job_input = job["input"]
    prompt = job_input.get("prompt")
    seconds = job_input.get("seconds", 0)
    
    # Simulate processing time
    time.sleep(seconds)
    
    return prompt

runpod.serverless.start({"handler": handler})
