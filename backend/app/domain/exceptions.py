"""
Domain-specific exceptions for the Document Intelligence system.

These are 'Base Exceptions'. They are caught by FastAPI 
exception handlers to return consistent HTTP status codes to the frontend.
"""

class AuthenticationFailed(Exception):
    """
    Raised when a user provides incorrect credentials (email/password) 
    or an invalid/expired JWT.
    
    Expected Result: 401 Unauthorized
    """
    pass

class NotAuthorized(Exception):
    """
    Raised when a user is authenticated but does not have permission 
    to access a specific resource (e.g., trying to view another user's document).
    
    Expected Result: 403 Forbidden
    """
    pass

class DocumentNotFound(Exception):
    """
    Raised when a requested Document ID does not exist in the database.
    
    Expected Result: 404 Not Found
    """
    pass

class ProcessingError(Exception):
    """
    Raised when the AI Processor (Gemini/Ollama) fails and we cannot 
    recover via retries.
    
    Expected Result: 500 Internal Server Error (or custom task failure)
    """
    pass