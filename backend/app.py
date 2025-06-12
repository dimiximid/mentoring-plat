from flask import Flask, request, jsonify, session
from flask_cors import CORS
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'https://*.vercel.app'])

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Mentoring platform API is running!"})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        
        # Register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": data['email'],
            "password": data['password']
        })
        
        if auth_response.user:
            # Create profile
            profile = supabase.table('profiles').insert({
                "id": auth_response.user.id,
                "name": data['name'],
                "role": data['role'],
                "expertise": data.get('expertise', ''),
                "bio": data.get('bio', '')
            }).execute()
            
            return jsonify({
                "success": True,
                "user": profile.data[0]
            }), 201
        else:
            return jsonify({"error": "Registration failed"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        
        # Login with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": data['email'],
            "password": data['password']
        })
        
        if auth_response.user:
            # Get user profile
            profile = supabase.table('profiles').select("*").eq('id', auth_response.user.id).execute()
            
            session['user_id'] = auth_response.user.id
            session['access_token'] = auth_response.session.access_token
            
            return jsonify({
                "success": True,
                "user": profile.data[0],
                "session": {
                    "access_token": auth_response.session.access_token,
                    "refresh_token": auth_response.session.refresh_token
                }
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        # Get token from session
        token = session.get('access_token')
        if token:
            supabase.auth.sign_out()
            session.clear()
        
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        profile = supabase.table('profiles').select("*").eq('id', user_id).execute()
        
        if profile.data:
            return jsonify({"success": True, "profile": profile.data[0]}), 200
        else:
            return jsonify({"error": "Profile not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/mentors', methods=['GET'])
def get_mentors():
    try:
        mentors = supabase.table('profiles').select("*").eq('role', 'mentor').execute()
        return jsonify({"success": True, "mentors": mentors.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/connections', methods=['POST'])
def create_connection():
    try:
        data = request.json
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Create connection request
        connection = supabase.table('connections').insert({
            "mentor_id": data['mentor_id'],
            "mentee_id": user_id,
            "status": "pending"
        }).execute()
        
        return jsonify({"success": True, "connection": connection.data[0]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/connections/<user_id>', methods=['GET'])
def get_connections(user_id):
    try:
        # Get connections where user is either mentor or mentee
        connections = supabase.table('connections').select("*").or_(
            f"mentor_id.eq.{user_id},mentee_id.eq.{user_id}"
        ).execute()
        
        return jsonify({"success": True, "connections": connections.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/messages', methods=['POST'])
def send_message():
    try:
        data = request.json
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Send message
        message = supabase.table('messages').insert({
            "sender_id": user_id,
            "receiver_id": data['receiver_id'],
            "content": data['content']
        }).execute()
        
        return jsonify({"success": True, "message": message.data[0]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    try:
        # Get messages where user is either sender or receiver
        messages = supabase.table('messages').select("*").or_(
            f"sender_id.eq.{user_id},receiver_id.eq.{user_id}"
        ).order('created_at', desc=False).execute()
        
        return jsonify({"success": True, "messages": messages.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# This is important for Render deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)