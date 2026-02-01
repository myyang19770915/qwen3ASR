#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001/ws/test-session-123"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully!")
            
            # 發送心跳測試
            await websocket.send("heartbeat")
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"Received: {response}")
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())