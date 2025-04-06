from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, app, login_required
from models import User

users_bp = Blueprint('users', __name__)

@users_bp.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    
    # Validate required fields
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 409
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already taken"}), 409
    
    try:
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            full_name=data.get('full_name', ''),
            nationality=data.get('nationality', ''),
            visa_type=data.get('visa_type', ''),
            arrival_date=data.get('arrival_date'),
            has_family=data.get('has_family', False),
            spouse_nationality=data.get('spouse_nationality', ''),
            num_children=data.get('num_children', 0),
            employment_status=data.get('employment_status', ''),
            german_level=data.get('german_level', '')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Don't return password hash
        user_data = {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'full_name': new_user.full_name,
            'onboarded': new_user.onboarded
        }
        
        return jsonify(user_data), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    # Ensure user can only access their own data
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'nationality': user.nationality,
        'visa_type': user.visa_type,
        'arrival_date': user.arrival_date.isoformat() if user.arrival_date else None,
        'has_family': user.has_family,
        'spouse_nationality': user.spouse_nationality,
        'num_children': user.num_children,
        'employment_status': user.employment_status,
        'german_level': user.german_level,
        'onboarded': user.onboarded,
        'created_at': user.created_at.isoformat()
    }
    
    return jsonify(user_data)

@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    # Ensure user can only update their own data
    if session.get('user_id') != user_id:
        return jsonify({"error": "Unauthorized"}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.json
    
    try:
        # Update user fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'nationality' in data:
            user.nationality = data['nationality']
        if 'visa_type' in data:
            user.visa_type = data['visa_type']
        if 'arrival_date' in data:
            user.arrival_date = data['arrival_date']
        if 'has_family' in data:
            user.has_family = data['has_family']
        if 'spouse_nationality' in data:
            user.spouse_nationality = data['spouse_nationality']
        if 'num_children' in data:
            user.num_children = data['num_children']
        if 'employment_status' in data:
            user.employment_status = data['employment_status']
        if 'german_level' in data:
            user.german_level = data['german_level']
        if 'onboarded' in data:
            user.onboarded = data['onboarded']
        
        # Only allow password update if old password is provided
        if 'new_password' in data and 'old_password' in data:
            if check_password_hash(user.password_hash, data['old_password']):
                user.password_hash = generate_password_hash(data['new_password'])
            else:
                return jsonify({"error": "Incorrect password"}), 401
        
        db.session.commit()
        
        return jsonify({"message": "User updated successfully"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Register blueprint
app.register_blueprint(users_bp)
