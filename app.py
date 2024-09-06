from flask import Flask, redirect, url_for, session, request, render_template
from flask_pymongo import PyMongo
from datetime import datetime
from dotenv import load_dotenv
import os
import requests

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# MongoDB setup
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb+srv://aylinambriz:<aylinambriz>@aylinambriz.adwsr.mongodb.net/auth_system")
mongo = PyMongo(app)

# Auth0 settings
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user_profile'))

@app.route('/login')
def login():
    return redirect(f"https://{AUTH0_DOMAIN}/authorize"
                    f"?response_type=code&client_id={AUTH0_CLIENT_ID}"
                    f"&redirect_uri=http://localhost:5000/callback"
                    f"&scope=openid%20profile%20email")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code provided", 400

    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        'grant_type': 'authorization_code',
        'client_id': AUTH0_CLIENT_ID,
        'client_secret': AUTH0_CLIENT_SECRET,
        'code': code,
        'redirect_uri': 'http://localhost:5000/callback'
    }
    token_headers = {'content-type': 'application/json'}
    
    try:
        token_info = requests.post(token_url, json=token_payload, headers=token_headers).json()
        access_token = token_info['access_token']
    except Exception as e:
        app.logger.error(f"Error obtaining access token: {str(e)}")
        return "Error during authentication", 500

    user_url = f'https://{AUTH0_DOMAIN}/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        user_info = requests.get(user_url, headers=headers).json()
    except Exception as e:
        app.logger.error(f"Error obtaining user info: {str(e)}")
        return "Error obtaining user information", 500

    try:
        users = mongo.db.users
        existing_user = users.find_one({'auth0_id': user_info['sub']})
        
        if not existing_user:
            user_data = {
                'auth0_id': user_info['sub'],
                'email': user_info['email'],
                'name': user_info.get('name', ''),
                'created_at': datetime.utcnow()
            }
            users.insert_one(user_data)
        
        session['user_profile'] = {
            'user_id': user_info['sub'],
            'name': user_info.get('name', ''),
            'email': user_info['email']
        }

        return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.error(f"Error interacting with database: {str(e)}")
        return "Error saving user information", 500

@app.route('/dashboard')
def dashboard():
    if 'user_profile' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html', user=session['user_profile'])

@app.route('/logout')
def logout():
    session.clear()
    # Make sure this matches exactly with what you've set in Auth0
    return_to = url_for('home', _external=True)
    logout_url = f'https://{AUTH0_DOMAIN}/v2/logout?client_id={AUTH0_CLIENT_ID}&returnTo={return_to}'
    return redirect(logout_url)

if __name__ == '__main__':
    app.run(debug=True)