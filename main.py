import asyncio
import json
import re
import paramiko
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles


ssh_app = FastAPI()
templates = Jinja2Templates(directory="templates")


ssh_app.mount("/static", StaticFiles(directory="static"), name="static")

ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

@ssh_app.get("/")
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@ssh_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ssh_client = None
    channel = None
    read_task = None

    try:
        # Receive connection details from the client
        data = await websocket.receive_text()
        connection_details = json.loads(data)

        # Extract SSH connection details
        hostname = connection_details.get("hostname")
        port = int(connection_details.get("port", 22))
        username = connection_details.get("username")
        password = connection_details.get("password")

        # Establish SSH connection using Paramiko
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, port, username, password)

        transport = ssh_client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.invoke_shell()

        async def read_from_channel():
            buffer = ""
            while True:
                if channel.recv_ready():
                    recv_data = channel.recv(1024).decode("utf-8")
                    buffer += recv_data
                    cleaned_output = ansi_escape.sub("", buffer)
                    await websocket.send_text(cleaned_output)
                    buffer = ""
                await asyncio.sleep(0.1)

        read_task = asyncio.create_task(read_from_channel())

        while True:
            data = await websocket.receive_text()
            if data:
                channel.send(data.encode("utf-8"))

    except WebSocketDisconnect:
        if read_task:
            read_task.cancel()
        if channel:
            channel.close()
        if ssh_client:
            ssh_client.close()
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        if read_task:
            read_task.cancel()
        if channel:
            channel.close()
        if ssh_client:
            ssh_client.close()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(ssh_app, host='0.0.0.0', port=8000)
