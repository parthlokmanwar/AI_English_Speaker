import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8001/ws/chat"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            payload = {
                "message": "Hello Maya, this is a test.",
                "history": [],
                "mode": "casual",
                "turn_count": 0
            }
            print("Sending payload...")
            await websocket.send(json.dumps(payload))
            
            while True:
                response = await websocket.recv()
                if isinstance(response, str):
                    data = json.loads(response)
                    if data.get("type") == "text":
                        print(data.get("content"), end="", flush=True)
                    elif data.get("type") == "feedback":
                        print("\n\n[Feedback received]:", json.dumps(data.get("data")))
                    elif data.get("type") == "done":
                        print("\n[Stream complete]")
                        break
                    elif data.get("type") == "error":
                        print("\n[Error]:", data.get("message"))
                        break
                else:
                    print(f"\n[Received binary audio chunk: {len(response)} bytes]")
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat())
