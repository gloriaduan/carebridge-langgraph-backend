from fastapi import FastAPI
import asyncio
import socketio
from agent_flow.graph import app
import json
from utils.socket_context import SocketIOContext

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

fastapi_app = FastAPI()

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
    users_location = data.get("location")

    asyncio.create_task(stream_data(sid, query, users_location))


async def stream_data(sid, query, location):
    print("stream_data called")

    SocketIOContext.set_context(sio, sid)

    try:
        async for chunk in app.astream(
            {"query": query, "users_location": location}, 
            stream_mode="updates"
        ):
            curr_chunk = chunk
            first_key = list(curr_chunk.keys())[0]
            
            # await sio.emit("update", {"message": f"finished {first_key}"}, room=sid)
            
            if first_key == "generate":
                if "error_response" in curr_chunk[first_key]:
                    error_response = curr_chunk[first_key]["error_response"]
                    print("Error response:", error_response)

                    await sio.emit(
                        "final_res",
                        {"message": "", "error_msg": error_response},
                        room=sid,
                    )
                    return

                structured_response = curr_chunk[first_key]["structured_response"]

                print("structured_response", structured_response)

                if hasattr(structured_response, "dict"):
                    response_dict = structured_response.dict()
                elif hasattr(structured_response, "to_dict"):
                    response_dict = structured_response.to_dict()
                else:
                    response_dict = vars(structured_response)

                await sio.emit(
                    "final_res",
                    {"message": json.dumps(response_dict)},
                    room=sid,
                )
                
    except Exception as e:
        await SocketIOContext.emit("error", {"message": str(e)})
        print(f"Error in stream_data: {e}")
        await sio.emit(
            "final_res",
            {"message": "", "error_msg": str(e)},
            room=sid,
        )



if __name__ == "__main__":
    test_query = "Find me pizza near place"
    print("Debugging LangGraph pipeline with test query:", test_query)
    # Synchronous invocation for debugging
    for chunk in app.stream({"query": test_query}, stream_mode="updates"):
        print("Chunk:", chunk)
