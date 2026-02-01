import os
import json
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Dict, Any
import asyncio
import uuid
from datetime import datetime

from audio_transcriber import AudioTranscriber

app = FastAPI(title="Audio Transcription API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003", "http://127.0.0.1:3003"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize transcriber
transcriber = AudioTranscriber()

# Store active transcription sessions
active_sessions: Dict[str, Dict[str, Any]] = {}

# Create uploads and results directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"[DEBUG] WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"[DEBUG] WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                print(f"[DEBUG] Sending message to {session_id}: {message['type']}")
                await self.active_connections[session_id].send_json(message)
                print(f"[DEBUG] Message sent successfully")
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
        else:
            print(f"[DEBUG] No active connection for session {session_id}")

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Audio Transcription API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload audio file and start transcription process."""
    
    # Check file format
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.mp3', '.wav', '.m4a']:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format: {file_extension}. Supported: .mp3, .wav, .m4a"
        )
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_dir = Path("uploads")
    file_path = upload_dir / f"{session_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Store session info
        active_sessions[session_id] = {
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded",
            "upload_time": datetime.now().isoformat()
        }
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/transcribe/{session_id}")
async def start_transcription(session_id: str):
    """Start transcription process for uploaded file."""
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    file_path = session["file_path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Update session status
    active_sessions[session_id]["status"] = "processing"
    
    # Start transcription in background
    asyncio.create_task(process_transcription(session_id, file_path))
    
    return {"message": "Transcription started", "session_id": session_id}

async def process_transcription(session_id: str, file_path: str):
    """Background task to process transcription."""
    
    print(f"[DEBUG] Starting transcription for session {session_id}")
    
    async def progress_callback(current: int, total: int, segment_info: dict):
        """Callback to send progress updates via WebSocket."""
        try:
            message = {
                "type": "progress",
                "current": current,
                "total": total,
                "segment": segment_info,
                "percentage": round((current / total) * 100, 2) if total > 0 else 0
            }
            print(f"[DEBUG] Sending progress update: {message}")
            await manager.send_message(session_id, message)
            print(f"[DEBUG] Progress update sent successfully")
        except Exception as e:
            print(f"Error sending progress update: {e}")
    
    try:
        # Perform transcription
        result = await transcriber.transcribe_file_async(file_path, progress_callback)
        
        if result["success"]:
            # Save result to file
            result_file = f"results/{session_id}_transcription.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Update session
            active_sessions[session_id].update({
                "status": "completed",
                "result_file": result_file,
                "completion_time": datetime.now().isoformat()
            })
            
            # Send completion message
            await manager.send_message(session_id, {
                "type": "completed",
                "result": result,
                "download_url": f"/download/{session_id}"
            })
        else:
            # Handle error
            active_sessions[session_id].update({
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "completion_time": datetime.now().isoformat()
            })
            
            await manager.send_message(session_id, {
                "type": "error",
                "error": result.get("error", "Transcription failed")
            })
            
    except Exception as e:
        active_sessions[session_id].update({
            "status": "error",
            "error": str(e),
            "completion_time": datetime.now().isoformat()
        })
        
        await manager.send_message(session_id, {
            "type": "error",
            "error": str(e)
        })

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "heartbeat", "message": "alive"})
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.get("/status/{session_id}")
async def get_status(session_id: str):
    """Get current status of transcription session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return active_sessions[session_id]

@app.get("/download/{session_id}")
async def download_result(session_id: str):
    """Download transcription result as JSON file."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail="Transcription not completed")
    
    result_file = session.get("result_file")
    if not result_file or not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    filename = f"{Path(session['filename']).stem}_transcription.json"
    
    return FileResponse(
        result_file,
        media_type="application/json",
        filename=filename
    )

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clean up session and associated files."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    # Clean up files
    try:
        if os.path.exists(session["file_path"]):
            os.remove(session["file_path"])
        
        result_file = session.get("result_file")
        if result_file and os.path.exists(result_file):
            os.remove(result_file)
        
        # Remove from active sessions
        del active_sessions[session_id]
        
        # Disconnect websocket
        manager.disconnect(session_id)
        
        return {"message": "Session deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    return {"sessions": active_sessions}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)