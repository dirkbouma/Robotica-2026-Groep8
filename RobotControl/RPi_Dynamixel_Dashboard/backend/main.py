import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from .models import RegisterUpdateRequest, MoveRequest, TorqueRequest, ScanResponse, GenericResponse
from .servo_controller import controller

app = FastAPI(title="Dynamixel AX-12A Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API ENDPOINTS
@app.get("/api/scan", response_model=ScanResponse)
async def scan_servos():
    ids = controller.scan()
    return ScanResponse(found_ids=ids)

@app.get("/api/servo/{servo_id}/registers")
async def get_registers(servo_id: int):
    regs = controller.get_all_registers(servo_id)
    return regs

@app.post("/api/servo/register", response_model=GenericResponse)
async def update_register(req: RegisterUpdateRequest):
    success = controller.write_register(req.servo_id, req.register_name, req.value)
    if success:
        return GenericResponse(success=True, message=f"Updated {req.register_name} to {req.value}")
    return GenericResponse(success=False, message="Failed to update register")

@app.post("/api/servo/move", response_model=GenericResponse)
async def move_servo(req: MoveRequest):
    success = controller.write_register(req.servo_id, "Goal Position", req.goal_position)
    return GenericResponse(success=success, message="Moved" if success else "Failed")

@app.post("/api/servo/torque", response_model=GenericResponse)
async def toggle_torque(req: TorqueRequest):
    val = 1 if req.enable else 0
    success = controller.write_register(req.servo_id, "Torque Enable", val)
    return GenericResponse(success=success, message="Torque toggled" if success else "Failed")


# WEBSOCKET FOR TELEMETRY
active_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # We wait for the client to send the list of servo IDs they want telemetry for
            data = await websocket.receive_text()
            req = json.loads(data)
            servo_ids = req.get("servo_ids", [])
            
            telemetry_data = {}
            for sid in servo_ids:
                telemetry_data[sid] = {
                    "Present Position": controller.read_register(sid, "Present Position"),
                    "Present Load": controller.read_register(sid, "Present Load"),
                    "Present Voltage": controller.read_register(sid, "Present Voltage"),
                    "Present Temperature": controller.read_register(sid, "Present Temperature"),
                }
            
            await websocket.send_json(telemetry_data)
            await asyncio.sleep(0.1) # Prevent flooding
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Mount frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
