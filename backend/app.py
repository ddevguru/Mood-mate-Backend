from flask import Flask, request, jsonify, send_from_directory
from flask_mysqldb import MySQL
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import io
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'sql12.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql12762188'  
app.config['MYSQL_PASSWORD'] = '4jGQ6rgQWp' 
app.config['MYSQL_DB'] = 'sql12762188'

mysql = MySQL(app)

# Upload Folder Configuration
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Define mood-based recommendations
mood_recommendations = {
    "Happy": ["Listen to upbeat songs", "Watch a comedy movie"],
    "Sad": ["Listen to relaxing music", "Read a motivational book"],
    "Angry": ["Try meditation", "Go for a run"],
    "Neutral": ["Learn a new skill", "Watch an educational video"]
}

def detect_mood(image):
    image = np.array(image)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    brightness = np.mean(gray)
    avg_color = np.mean(image, axis=(0, 1))
    blue, green, red = avg_color

    if brightness > 150 and red > green and red > blue:
        return "Happy"
    elif brightness < 100 and blue > red and blue > green:
        return "Sad"
    elif red > 150 and brightness < 130:
        return "Angry"
    else:
        return "Neutral"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files or 'username' not in request.form:
            return jsonify({"error": "Missing file or username"}), 400

        file = request.files['file']
        username = request.form['username']

        image = Image.open(io.BytesIO(file.read())).convert('RGB')
        image = image.resize((48, 48))

        detected_mood = detect_mood(image)
        recommendations = mood_recommendations.get(detected_mood, ["No recommendations available"])
        recommendations_text = ', '.join(recommendations)  
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO mood_history (username, mood, recommendations, timestamp) VALUES (%s, %s, %s, %s)",
                    (username, detected_mood, recommendations_text, timestamp))
        mysql.connection.commit()
        cur.close()

        return jsonify({"mood": detected_mood, "recommendations": recommendations})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/register', methods=['POST'])
def register():
    try:
        required_fields = ['name', 'email', 'username', 'password', 'mobile']
        for field in required_fields:
            if field not in request.form:
                return jsonify({'error': f'{field} is required'}), 400

        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        mobile = request.form['mobile']

        profile_image = request.files.get('profile_image')
        filename = None  # Default if no image is provided

        if profile_image and allowed_file(profile_image.filename):
            filename = secure_filename(profile_image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_image.save(image_path)

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users (name, email, username, password, mobile, profile_image) VALUES (%s, %s, %s, %s, %s, %s)", 
            (name, email, username, password, mobile, filename)
        )
        mysql.connection.commit()
        cur.close()

        return jsonify({'message': 'Registration successful'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400

        email = data['email']
        password = data['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, email, profile_image FROM users WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()

        if user:
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user[0],
                    'name': user[1],
                    'email': user[2],
                    'profile_image': f"http://127.0.0.1:5000/uploads/{user[3]}" if user[3] else None
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid email or password'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET'])
def profile():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email parameter missing"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name, email, username, mobile, profile_image FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if user:
        # Construct full image URL dynamically
        base_url = "http://10.0.2.2:5000/uploads/"  # Emulator URL for local development
        image_url = base_url + user[5] if user[5] else None

        return jsonify({
            'user': {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'username': user[3],
                'mobile': user[4],
                'profile_image': image_url,  # Send full image URL
            }
        }), 200
    else:
        return jsonify({'error': 'User not found'}), 404

# ✅ Route to Serve Uploaded Images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/get_mood_history', methods=['GET'])
def get_mood_history():
    username = request.args.get('username')

    if not username:
        return jsonify({"error": "Username is required"}), 400

    try:
        cur = mysql.connection.cursor()
        query = "SELECT mood, timestamp, recommendations FROM mood_history WHERE username = %s ORDER BY timestamp DESC"
        cur.execute(query, (username,))
        history = cur.fetchall()

        if not history:
            return jsonify([]), 200  # Return an empty list instead of a dictionary

        # Convert tuple to dictionary
        history_list = [
            {"mood": row[0], "timestamp": row[1], "recommendations": row[2]}
            for row in history
        ]

        return jsonify(history_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
