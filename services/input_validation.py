"""Validation for profile data submitted through the external API.

All fields are optional; only values that are present are validated.
Matching is case-insensitive and aligned with the pipeline engine's
visa mapping so validation never rejects values the app itself produces.
"""
from datetime import datetime

from services.pipeline_engine import VISA_TYPE_MAPPING

VALID_GERMAN_LEVELS = {'none', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2', 'native'}
VALID_EMPLOYMENT_STATUSES = {
    'employed', 'self-employed', 'self_employed', 'student',
    'unemployed', 'retired', 'job_seeking', 'tech_professional'
}


class InputValidator:

    @staticmethod
    def validate_profile_data(data):
        """Validate profile/onboarding data.

        Returns {field: [error messages]}; empty dict when valid.
        """
        errors = {}

        full_name = (data.get('full_name') or '').strip()
        if len(full_name) > 120:
            errors['full_name'] = ['Full name must be less than 120 characters']

        nationality = (data.get('nationality') or '').strip()
        if len(nationality) > 64:
            errors['nationality'] = ['Nationality must be less than 64 characters']

        visa_type = (data.get('visa_type') or '').strip().lower()
        if visa_type and visa_type != 'other' and visa_type not in VISA_TYPE_MAPPING:
            errors['visa_type'] = ['Unknown visa type']

        german_level = (data.get('german_level') or '').strip().lower()
        if german_level and german_level not in VALID_GERMAN_LEVELS:
            errors['german_level'] = ['Unknown German proficiency level']

        employment_status = (data.get('employment_status') or '').strip().lower()
        if employment_status and employment_status not in VALID_EMPLOYMENT_STATUSES:
            errors['employment_status'] = ['Unknown employment status']

        num_children = data.get('num_children')
        if num_children is not None:
            try:
                if not (0 <= int(num_children) <= 20):
                    errors['num_children'] = ['Number of children must be between 0 and 20']
            except (ValueError, TypeError):
                errors['num_children'] = ['Number of children must be a whole number']

        arrival_date = data.get('arrival_date')
        if arrival_date:
            try:
                parsed = datetime.fromisoformat(str(arrival_date).replace('Z', '+00:00'))
                now = datetime.now()
                if not (now.year - 3 <= parsed.year <= now.year + 3):
                    errors['arrival_date'] = ['Arrival date must be within a few years of today']
            except ValueError:
                errors['arrival_date'] = ['Arrival date must be an ISO date (YYYY-MM-DD)']

        return errors
