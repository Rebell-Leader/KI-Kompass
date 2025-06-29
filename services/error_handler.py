import logging
import traceback
from typing import Dict, Any, Optional
from flask import request, jsonify, render_template
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    Centralized error handling service for consistent error responses
    """
    
    @staticmethod
    def handle_api_error(error: Exception, user_friendly_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle API errors and return consistent JSON response
        """
        error_id = id(error)  # Generate unique error ID for tracking
        
        # Log the full error details
        logger.error(f"API Error {error_id}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Determine error type and appropriate response
        if isinstance(error, ValueError):
            status_code = 400
            error_type = "validation_error"
            message = user_friendly_message or "Invalid input provided"
        elif isinstance(error, PermissionError):
            status_code = 403
            error_type = "permission_error"
            message = user_friendly_message or "You don't have permission to perform this action"
        elif isinstance(error, FileNotFoundError):
            status_code = 404
            error_type = "not_found"
            message = user_friendly_message or "The requested resource was not found"
        elif isinstance(error, ConnectionError):
            status_code = 503
            error_type = "service_unavailable"
            message = user_friendly_message or "External service is temporarily unavailable"
        elif isinstance(error, TimeoutError):
            status_code = 504
            error_type = "timeout"
            message = user_friendly_message or "Request timed out, please try again"
        else:
            status_code = 500
            error_type = "internal_error"
            message = user_friendly_message or "An unexpected error occurred"
        
        response = {
            "error": True,
            "error_type": error_type,
            "message": message,
            "error_id": error_id
        }
        
        # Add debug info in development
        if logger.isEnabledFor(logging.DEBUG):
            response["debug_info"] = {
                "error_class": error.__class__.__name__,
                "error_details": str(error)
            }
        
        return response, status_code
    
    @staticmethod
    def handle_form_errors(errors: Dict[str, list], flash_message: str = "Please correct the errors below") -> str:
        """
        Handle form validation errors consistently
        """
        # Log form errors for debugging
        logger.warning(f"Form validation errors: {errors}")
        
        # Create user-friendly error message
        error_messages = []
        for field, field_errors in errors.items():
            field_name = field.replace('_', ' ').title()
            for error in field_errors:
                error_messages.append(f"{field_name}: {error}")
        
        return f"{flash_message}. {'; '.join(error_messages)}"
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str = "database operation") -> Dict[str, Any]:
        """
        Handle database-related errors
        """
        error_id = id(error)
        logger.error(f"Database Error {error_id} during {operation}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Check for specific database error types
        error_str = str(error).lower()
        
        if "connection" in error_str or "connect" in error_str:
            message = "Database connection failed. Please try again later."
            error_type = "database_connection"
        elif "timeout" in error_str:
            message = "Database operation timed out. Please try again."
            error_type = "database_timeout"
        elif "unique constraint" in error_str or "duplicate" in error_str:
            message = "This information already exists in the system."
            error_type = "duplicate_data"
        elif "foreign key" in error_str:
            message = "Cannot perform this operation due to data dependencies."
            error_type = "data_dependency"
        else:
            message = "A database error occurred. Please try again later."
            error_type = "database_error"
        
        return {
            "error": True,
            "error_type": error_type,
            "message": message,
            "error_id": error_id
        }, 500
    
    @staticmethod
    def handle_llm_error(error: Exception) -> Dict[str, Any]:
        """
        Handle LLM/AI service related errors
        """
        error_id = id(error)
        logger.error(f"LLM Error {error_id}: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        error_str = str(error).lower()
        
        if "api key" in error_str or "authentication" in error_str:
            message = "AI service authentication failed. Please contact support."
            error_type = "ai_auth_error"
        elif "timeout" in error_str or "time" in error_str:
            message = "AI service is taking too long to respond. Please try a shorter question."
            error_type = "ai_timeout"
        elif "rate limit" in error_str or "quota" in error_str:
            message = "AI service rate limit exceeded. Please try again later."
            error_type = "ai_rate_limit"
        elif "context length" in error_str or "token" in error_str:
            message = "Your question is too complex. Please try breaking it into smaller parts."
            error_type = "ai_context_limit"
        else:
            message = "AI service is temporarily unavailable. Please try again later."
            error_type = "ai_service_error"
        
        return {
            "error": True,
            "error_type": error_type,
            "message": message,
            "error_id": error_id
        }
    
    @staticmethod
    def handle_web_scraping_error(error: Exception, url: str = "unknown") -> Dict[str, Any]:
        """
        Handle web scraping related errors
        """
        error_id = id(error)
        logger.error(f"Web Scraping Error {error_id} for URL {url}: {str(error)}")
        
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            message = "The external website is taking too long to respond."
            error_type = "scraping_timeout"
        elif "connection" in error_str or "network" in error_str:
            message = "Cannot connect to the external website."
            error_type = "scraping_connection"
        elif "403" in error_str or "forbidden" in error_str:
            message = "Access to the external website was denied."
            error_type = "scraping_forbidden"
        elif "404" in error_str or "not found" in error_str:
            message = "The requested page was not found on the external website."
            error_type = "scraping_not_found"
        else:
            message = "Unable to retrieve information from the external website."
            error_type = "scraping_error"
        
        return {
            "error": True,
            "error_type": error_type,
            "message": message,
            "error_id": error_id,
            "fallback_action": "Using cached information instead"
        }
    
    @staticmethod
    def create_error_response(message: str, error_type: str = "general_error", status_code: int = 400) -> tuple:
        """
        Create a standardized error response tuple for Flask routes
        """
        return jsonify({
            "error": True,
            "error_type": error_type,
            "message": message
        }), status_code
    
    @staticmethod
    def log_performance_warning(operation: str, duration: float, threshold: float = 5.0):
        """
        Log performance warnings for slow operations
        """
        if duration > threshold:
            logger.warning(f"Performance warning: {operation} took {duration:.2f} seconds (threshold: {threshold}s)")
    
    @staticmethod
    def is_user_error(error: Exception) -> bool:
        """
        Determine if an error is caused by user input (4xx) or system issue (5xx)
        """
        user_error_types = (ValueError, TypeError, KeyError, AttributeError)
        return isinstance(error, user_error_types) or isinstance(error, HTTPException) and 400 <= error.code < 500