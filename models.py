from pydantic import BaseModel

class User(BaseModel):
    username: str
    role: str

class Document(BaseModel):
    title: str
    content: str
    posted_by: str
    role: str
    filename: str
