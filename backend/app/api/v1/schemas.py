from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

# --- AUTHENTICATION SCHEMAS ---

class LoginRequest(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    """Schema for new user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = Field(None, description="User's full name for personalization")

class ResgisterResponse(BaseModel):
    """Schema for registration response."""
    id: str = Field(..., description="Unique identifier of the newly created user")
    email: EmailStr = Field(..., description="Email address of the newly created user")
    full_name: str | None = Field(None, description="User's full name")
    role: str = Field(..., description="Role assigned to the new user")
    access_token: str | None = Field(None, description="JWT access token for auto-login")
    refresh_token: str | None = Field(None, description="JWT refresh token for auto-login")
    token_type: str = Field("bearer", description="Type of token issued")
    message: str = Field(..., description="Confirmation message about account creation")



# --- DOCUMENT SCHEMAS ---

class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    message: str = Field(..., description="Confirmation message about the upload")
    document_id: str = Field(..., description="Unique identifier of the uploaded document")
    task_id: str = Field(..., description="Identifier of the background analysis task")
    status: str = Field(..., description="Current status of the document processing")
    file_name: str = Field(..., description="Original name of the uploaded file")
    url: str = Field(..., description="URL where the uploaded document can be accessed")
    owner: EmailStr = Field(..., description="Email address of the user who owns the document")


class DocumentAnalysisResponse(BaseModel):
    """Schema for document analysis results."""
    id: str = Field(..., description="Unique identifier of the document")
    file_name: str = Field(..., description="Original name of the uploaded file")
    url: str = Field(..., description="URL where the uploaded document can be accessed")
    owner: EmailStr = Field(..., description="Email address of the user who owns the document")
    status: str = Field(..., description="Current status of the document processing")
    analysis_results: dict = Field(..., description="Structured results from the document analysis")
    created_at: datetime = Field(..., description="Timestamp when the document was uploaded")

# --- RAG SCHEMAS ---

class QueryRequest(BaseModel):
    """Schema for querying a document."""
    query: str = Field(..., description="The question or query about the document")

class SourceNode(BaseModel):
    """Schema for a source reference node."""
    text: str = Field(..., description="The content of the source chunk")
    score: float = Field(..., description="Relevance score of the chunk")
    metadata: dict = Field(..., description="Metadata associated with the chunk")

class QueryResponse(BaseModel):
    """Schema for query response."""
    answer: str = Field(..., description="The AI-generated answer to the query")
    sources: list[SourceNode] = Field(..., description="Reference chunks used to generate the answer")
