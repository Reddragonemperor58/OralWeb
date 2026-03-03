from pydantic import BaseModel
from typing import Optional

# User Schemas
class UserCreate(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    email: str
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    email: str
    id: int

# Patient Schemas
class PatientCreate(BaseModel):
    name: str
    age: int
    contact: str
    gender: str

class PatientOut(PatientCreate):
    id: int
    doctor_id: int
    class Config:
        orm_mode = True