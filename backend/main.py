from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import analysis  # We will create this
import auth      # We will create this
import models, schemas, database

# Initialize DB
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Oral Diagnosis SaaS API")

# --- AUTHENTICATION ENDPOINTS ---
@app.post("/signup", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = auth.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return auth.create_user(db=db, user=user)

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- CLINICAL ENDPOINTS ---
@app.get("/patients", response_model=list[schemas.PatientOut])
def read_patients(current_user: schemas.User = Depends(auth.get_current_active_user), db: Session = Depends(database.get_db)):
    # Only return patients belonging to the logged-in doctor
    return db.query(models.Patient).filter(models.Patient.doctor_id == current_user.id).all()

@app.post("/patients", response_model=schemas.PatientOut)
def create_patient(patient: schemas.PatientCreate, current_user: schemas.User = Depends(auth.get_current_active_user), db: Session = Depends(database.get_db)):
    db_patient = models.Patient(**patient.dict(), doctor_id=current_user.id)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

# --- AI ANALYSIS ENDPOINTS ---
@app.post("/analyze/ssim")
async def analyze_ssim(file1: UploadFile = File(...), file2: UploadFile = File(...), current_user: schemas.User = Depends(auth.get_current_active_user)):
    # Read image bytes
    img1_bytes = await file1.read()
    img2_bytes = await file2.read()
    
    # Process using the helper module
    result = analysis.calculate_ssim(img1_bytes, img2_bytes)
    return result

@app.post("/analyze/dl")
async def analyze_dl(file: UploadFile = File(...), current_user: schemas.User = Depends(auth.get_current_active_user)):
    img_bytes = await file.read()
    result = analysis.predict_dl(img_bytes)
    return result