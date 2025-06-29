import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)

class InputValidator:
    """
    Comprehensive input validation service for form inputs and API requests
    """
    
    @staticmethod
    def validate_user_registration(form_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate user registration form data
        Returns dict with field names as keys and list of error messages as values
        """
        errors = {}
        
        # Username validation
        username = form_data.get('username', '').strip()
        if not username:
            errors['username'] = ['Username is required']
        elif len(username) < 3:
            errors['username'] = ['Username must be at least 3 characters long']
        elif len(username) > 64:
            errors['username'] = ['Username must be less than 64 characters']
        elif not re.match(r'^[a-zA-Z0-9_-]+$', username):
            errors['username'] = ['Username can only contain letters, numbers, hyphens, and underscores']
        
        # Email validation
        email = form_data.get('email', '').strip().lower()
        if not email:
            errors['email'] = ['Email is required']
        else:
            try:
                # Use email-validator library for robust email validation
                validate_email(email)
            except EmailNotValidError:
                errors['email'] = ['Please enter a valid email address']
        
        # Password validation
        password = form_data.get('password', '')
        if not password:
            errors['password'] = ['Password is required']
        elif len(password) < 8:
            errors['password'] = ['Password must be at least 8 characters long']
        elif len(password) > 128:
            errors['password'] = ['Password must be less than 128 characters']
        elif not re.search(r'[A-Za-z]', password):
            errors['password'] = ['Password must contain at least one letter']
        elif not re.search(r'[0-9]', password):
            errors['password'] = ['Password must contain at least one number']
        
        return errors
    
    @staticmethod
    def validate_profile_data(form_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate user profile/onboarding form data
        """
        errors = {}
        
        # Full name validation
        full_name = form_data.get('full_name', '').strip()
        if full_name and len(full_name) > 120:
            errors['full_name'] = ['Full name must be less than 120 characters']
        elif full_name and not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', full_name):
            errors['full_name'] = ['Full name contains invalid characters']
        
        # Nationality validation
        nationality = form_data.get('nationality', '').strip()
        if nationality and len(nationality) > 64:
            errors['nationality'] = ['Nationality must be less than 64 characters']
        
        # Visa type validation
        visa_type = form_data.get('visa_type', '').strip()
        valid_visa_types = [
            'eu_citizen', 'eu_family', 'blue_card', 'work_permit', 'freelancer', 
            'entrepreneur', 'job_seeker', 'student', 'language_course', 'research',
            'family_reunion', 'spouse', 'child_reunion', 'humanitarian', 'refugee', 'asylum'
        ]
        if visa_type and visa_type not in valid_visa_types:
            errors['visa_type'] = ['Please select a valid visa type']
        
        # Arrival date validation
        arrival_date = form_data.get('arrival_date')
        if arrival_date:
            try:
                parsed_date = datetime.strptime(arrival_date, '%Y-%m-%d')
                # Check if date is reasonable (not too far in past or future)
                now = datetime.now()
                if parsed_date.year < now.year - 2:
                    errors['arrival_date'] = ['Arrival date seems too far in the past']
                elif parsed_date.year > now.year + 2:
                    errors['arrival_date'] = ['Arrival date seems too far in the future']
            except ValueError:
                errors['arrival_date'] = ['Please enter a valid date in YYYY-MM-DD format']
        
        # Employment status validation
        employment_status = form_data.get('employment_status', '').strip()
        valid_employment_statuses = ['employed', 'self-employed', 'student', 'unemployed', 'retired']
        if employment_status and employment_status not in valid_employment_statuses:
            errors['employment_status'] = ['Please select a valid employment status']
        
        # German level validation
        german_level = form_data.get('german_level', '').strip()
        valid_german_levels = ['none', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2']
        if german_level and german_level not in valid_german_levels:
            errors['german_level'] = ['Please select a valid German proficiency level']
        
        # Number of children validation
        num_children = form_data.get('num_children')
        if num_children is not None:
            try:
                num_children_int = int(num_children)
                if num_children_int < 0:
                    errors['num_children'] = ['Number of children cannot be negative']
                elif num_children_int > 20:
                    errors['num_children'] = ['Number of children seems unrealistic']
            except (ValueError, TypeError):
                errors['num_children'] = ['Please enter a valid number for children']
        
        return errors
    
    @staticmethod
    def validate_chat_message(message_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate chat message input
        """
        errors = {}
        
        query = message_data.get('query', '').strip()
        if not query:
            errors['query'] = ['Message cannot be empty']
        elif len(query) > 2000:
            errors['query'] = ['Message is too long (maximum 2000 characters)']
        elif len(query) < 2:
            errors['query'] = ['Message is too short (minimum 2 characters)']
        
        # Check for potential spam or abuse
        if query and InputValidator._is_potential_spam(query):
            errors['query'] = ['Message appears to contain spam or inappropriate content']
        
        return errors
    
    @staticmethod
    def validate_task_update(task_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate task status update data
        """
        errors = {}
        
        # Task ID validation
        task_id = task_data.get('task_id')
        if not task_id:
            errors['task_id'] = ['Task ID is required']
        else:
            try:
                task_id_int = int(task_id)
                if task_id_int <= 0:
                    errors['task_id'] = ['Invalid task ID']
            except (ValueError, TypeError):
                errors['task_id'] = ['Task ID must be a valid number']
        
        # Completed status validation
        completed = task_data.get('completed')
        if completed is not None and not isinstance(completed, bool):
            errors['completed'] = ['Completed status must be true or false']
        
        # Notes validation
        notes = task_data.get('notes', '').strip()
        if notes and len(notes) > 1000:
            errors['notes'] = ['Notes must be less than 1000 characters']
        
        return errors
    
    @staticmethod
    def _is_potential_spam(text: str) -> bool:
        """
        Basic spam detection for chat messages
        """
        text_lower = text.lower()
        
        # Check for excessive repetition
        words = text_lower.split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return True
        
        # Check for common spam patterns
        spam_patterns = [
            r'http[s]?://[^\s]+',  # URLs
            r'www\.[^\s]+',        # Website addresses
            r'\b(?:buy|sell|click|download|free|money|cash|win|winner)\b.*\b(?:now|today|here)\b',
            r'[A-Z]{5,}',          # Excessive capitals
            r'(.)\1{4,}',          # Repeated characters (aaaaaaa)
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @staticmethod
    def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input by removing dangerous characters and trimming
        """
        if not text:
            return ""
        
        # Remove potential XSS characters
        sanitized = re.sub(r'[<>"\']', '', text)
        
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Trim to max length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length].strip()
        
        return sanitized.strip()
    
    @staticmethod
    def validate_api_request(request_data: Dict[str, Any], required_fields: List[str]) -> Dict[str, List[str]]:
        """
        Generic API request validation
        """
        errors = {}
        
        # Check for required fields
        for field in required_fields:
            if field not in request_data or not request_data[field]:
                if field not in errors:
                    errors[field] = []
                errors[field].append(f'{field.replace("_", " ").title()} is required')
        
        return errors