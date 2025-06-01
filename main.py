from fastapi import FastAPI
import asyncio
import socketio
import uvicorn
from agent_flow.graph import app
import json

# Create a Socket.IO server instance with CORS enabled
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# Create FastAPI app
fastapi_app = FastAPI()

# Create the ASGI app by mounting the Socket.IO
app_asgi = socketio.ASGIApp(sio, fastapi_app)


@sio.event
async def connect(sid, environ):
    print("Client connected:", sid)


@sio.event
async def disconnect(sid):
    print("Client disconnected:", sid)


@sio.event
async def on_submit_query(sid, data):
    print("Received query:", sid, data)
    query = data.get("query")

    asyncio.create_task(stream_data(sid, query))


async def stream_data(sid, query):
    print("stream_data called")
    for chunk in app.stream({"query": query}, stream_mode="updates"):
        curr_chunk = chunk
        first_key = list(curr_chunk.keys())[0]
        await sio.emit("update", {"message": f"finished {first_key}"}, room=sid)
        if first_key == "generate":
            structured_response = curr_chunk[first_key]["structured_response"]
            # Convert AgentResponse to dict if possible
            print("structured_response", structured_response)
            if hasattr(structured_response, "dict"):
                response_dict = structured_response.dict()
            elif hasattr(structured_response, "to_dict"):
                response_dict = structured_response.to_dict()
            else:
                response_dict = vars(structured_response)
            print(response_dict)
            await sio.emit(
                "final_res",
                {"message": json.dumps(response_dict)},
                room=sid,
            )
