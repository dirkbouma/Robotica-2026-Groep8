from pydantic import BaseModel
from typing import Dict, Any, List

class RegisterUpdateRequest(BaseModel):
    servo_id: int
    register_name: str
    value: int

class MoveRequest(BaseModel):
    servo_id: int
    goal_position: int

class TorqueRequest(BaseModel):
    servo_id: int
    enable: bool

class ScanResponse(BaseModel):
    found_ids: List[int]

class GenericResponse(BaseModel):
    success: bool
    message: str
