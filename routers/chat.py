from flask import Blueprint, request, jsonify, session
from app import db, app, login_required
from models import User
from services.ai_assistant import get_ai_response

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Get AI response using Langchain
        response = get_ai_response(query, user)
        
        return jsonify({
            "query": query,
            "response": response
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Register blueprint
app.register_blueprint(chat_bp)
