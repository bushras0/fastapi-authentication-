from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pymongo import MongoClient
from pydantic import BaseModel
from typing import List
import os
import pdfplumber
from auth import get_current_user, hash_password, authenticate_user, create_access_token
from models import User, Document

app = FastAPI()

# MongoDB connection
client = MongoClient("mongodb+srv://cyberify:database@connection.4card.mongodb.net/notes?retryWrites=true&w=majority")
db = client["notes"]

# Collections
users_collection = db["users"]
documents_collection = db["documents"]

# Directory to save uploaded files
UPLOAD_DIRECTORY = "uploaded_files"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Pydantic model for User registration
class UserRegistration(BaseModel):
    username: str
    password: str
    role: str = "employee"  # Default role is employee

# POST route for user registration
@app.post("/register", response_model=UserRegistration)
async def register_user(user: UserRegistration):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = hash_password(user.password)
    users_collection.insert_one({"username": user.username, "password": hashed_password, "role": user.role})

    return user

# POST route for user login
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}

# POST route for creating documents with file upload
@app.post("/document", response_model=Document)
async def create_document(
    title: str = File(...),
    content: str = File(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    document = {
        "title": title,
        "posted_by": current_user.username,
        "role": current_user.role,
        "filename": file.filename
    }

    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # Extract text from PDF files
    if file.filename.endswith('.pdf'):
        with pdfplumber.open(file_location) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            document["content"] = text  # Store extracted content
    else:
        document["content"] = content  # Store content directly for non-PDF files

    documents_collection.insert_one(document)
    return document

# GET route for retrieving documents
@app.get("/documents", response_model=List[Document])
async def get_documents(current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        documents = list(documents_collection.find({}))
    else:
        documents = list(documents_collection.find({"posted_by": current_user.username}))

    return [{"title": doc["title"], "content": doc["content"], "posted_by": doc["posted_by"], "filename": doc["filename"]} for doc in documents]
