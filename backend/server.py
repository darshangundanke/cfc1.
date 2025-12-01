from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import io
import openpyxl
from openpyxl.styles import Font, Alignment

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Admin credentials (in production, use hashed passwords and environment variables)
ADMIN_USERNAME = "admin_kamch"
ADMIN_PASSWORD = "admin_kamch123"

# Models
class Answer(BaseModel):
    question_id: int
    value: int  # 1-5 (Never=1, Rarely=2, Occasionally=3, Frequently=4, Always=5)

class AssessmentSubmission(BaseModel):
    name: str
    age: str
    gender: str
    date: str
    mobile: str
    answers: List[Answer]

class Assessment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    age: str
    gender: str
    date: str
    mobile: str
    answers: List[Answer]
    score: int
    result: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    mobile: str
    email: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactRequestCreate(BaseModel):
    name: str
    mobile: str
    email: Optional[str] = None
    message: str

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str

def calculate_score_and_result(answers: List[Answer]):
    """Calculate total score and determine result"""
    total_score = sum(answer.value for answer in answers)
    
    if total_score <= 28:
        result = "Ama not present"
    elif total_score <= 42:
        result = "Ama slightly present"
    else:
        result = "Ama Present"
    
    return total_score, result

# Routes
@api_router.post("/assessments", response_model=Assessment)
async def create_assessment(submission: AssessmentSubmission):
    """Submit assessment form"""
    # Calculate score and result
    score, result = calculate_score_and_result(submission.answers)
    
    # Create assessment object
    assessment = Assessment(
        name=submission.name,
        age=submission.age,
        gender=submission.gender,
        date=submission.date,
        mobile=submission.mobile,
        answers=submission.answers,
        score=score,
        result=result
    )
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = assessment.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    # Convert answers to dict
    doc['answers'] = [answer.model_dump() if hasattr(answer, 'model_dump') else answer for answer in doc['answers']]
    
    await db.assessments.insert_one(doc)
    
    return assessment

@api_router.post("/contact-requests", response_model=ContactRequest)
async def create_contact_request(request: ContactRequestCreate):
    """Submit contact/callback request"""
    contact_req = ContactRequest(
        name=request.name,
        mobile=request.mobile,
        email=request.email,
        message=request.message
    )
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = contact_req.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.contact_requests.insert_one(doc)
    
    return contact_req

@api_router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(login: AdminLogin):
    """Admin login endpoint"""
    if login.username == ADMIN_USERNAME and login.password == ADMIN_PASSWORD:
        return AdminLoginResponse(success=True, message="Login successful")
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@api_router.get("/admin/assessments", response_model=List[Assessment])
async def get_all_assessments():
    """Get all assessments (admin only)"""
    # In production, add proper authentication middleware
    assessments = await db.assessments.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10000)
    
    # Convert ISO string timestamps back to datetime objects
    for assessment in assessments:
        if isinstance(assessment['timestamp'], str):
            assessment['timestamp'] = datetime.fromisoformat(assessment['timestamp'])
    
    return assessments

@api_router.get("/admin/assessments/export")
async def export_assessments():
    """Export assessments to Excel"""
    # Fetch all assessments
    assessments = await db.assessments.find({}, {"_id": 0}).sort("timestamp", -1).to_list(10000)
    
    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Assessments"
    
    # Add headers
    headers = ['Date Submitted', 'Name', 'Age', 'Gender', 'Date', 'Mobile', 'Score', 'Result']
    ws.append(headers)
    
    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Add data
    for assessment in assessments:
        timestamp = assessment.get('timestamp', '')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        ws.append([
            timestamp,
            assessment.get('name', ''),
            assessment.get('age', ''),
            assessment.get('gender', ''),
            assessment.get('date', ''),
            assessment.get('mobile', ''),
            assessment.get('score', ''),
            assessment.get('result', '')
        ])
    
    # Adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to bytes
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    # Return as streaming response
    headers = {
        'Content-Disposition': 'attachment; filename="kamch_assessments.xlsx"'
    }
    
    return StreamingResponse(
        excel_file,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers
    )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()