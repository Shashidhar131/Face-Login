import os
import pickle
import io
import base64
import datetime
from flask import Flask, request, jsonify
import numpy as np
from PIL import Image
import face_recognition

app = Flask(__name__)

DATA_FILE = 'user_data.pkl'
LOGIN_HISTORY_FILE = 'login_history.pkl'

# Load stored users from file
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

# Save users to file
def save_users(users):
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(users, f)

# Load login history
def load_login_history():
    if os.path.exists(LOGIN_HISTORY_FILE):
        with open(LOGIN_HISTORY_FILE, 'rb') as f:
            return pickle.load(f)
    return []

# Save login history
def save_login_history(history):
    with open(LOGIN_HISTORY_FILE, 'wb') as f:
        pickle.dump(history, f)

# Helper: Convert base64 image to numpy array
def base64_to_image(image_b64):
    header, encoded = image_b64.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(img_bytes))
    return np.array(image)

users = load_users()  # users dict: {username: face_encoding numpy array}
login_history = load_login_history()  # List of dicts {username, timestamp}

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Real-Time Face Login System - Python</title>
<style>
  body {
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    min-height: 100vh;
  }
  h1 {
    margin: 20px;
    user-select: none;
  }
  #container {
    background: rgba(0,0,0,0.5);
    border-radius: 15px;
    padding: 20px;
    width: 360px;
    margin-bottom: 40px;
  }
  label {
    display: block;
    margin-top: 10px;
    font-weight: bold;
  }
  input[type='text'] {
    width: 100%;
    padding: 8px;
    border-radius: 6px;
    border: none;
    margin-top: 6px;
    font-size: 16px;
  }
  button {
    width: 100%;
    margin-top: 15px;
    padding: 12px 0;
    font-weight: bold;
    font-size: 16px;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    background-color: #845ec2;
    color: white;
    transition: background-color 0.3s ease;
  }
  button:hover {
    background-color: #9b5de5;
  }
  video {
    border-radius: 10px;
    width: 320px;
    height: 240px;
    background: black;
    user-select: none;
  }
  #message {
    margin: 10px 0 0;
    font-weight: bold;
  }
  nav {
    margin: 20px 0;
  }
  nav button {
    background: #512da8;
    margin: 0 10px;
    width: 140px;
  }
  nav button.active {
    background: #ffd600;
    color: #512da8;
  }
  #loginHistoryContainer {
    background: rgba(0,0,0,0.3);
    border-radius: 10px;
    max-height: 200px;
    overflow-y: auto;
    padding: 15px;
    margin-top: 20px;
  }
  #loginHistoryContainer h2 {
    margin-top: 0;
    font-size: 18px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 6px;
  }
  ul#loginHistoryList {
    list-style: none;
    padding-left: 0;
    font-size: 14px;
    user-select: text;
  }
  ul#loginHistoryList li {
    margin-bottom: 8px;
    border-bottom: 1px dotted #ccc;
    padding-bottom: 4px;
  }
</style>
</head>
<body>
<h1>Real-Time Face Login System</h1>
<nav>
  <button id="registerBtn" class="active">Register</button>
  <button id="loginBtn">Login</button>
</nav>
<div id="container">
  <div id="registerSection">
    <label for="username">Username:</label>
    <input type="text" id="username" placeholder="Enter username" autocomplete="off"/>
    <video id="videoRegister" autoplay muted></video>
    <button id="captureRegister">Register Face</button>
    <div id="messageRegister"></div>
  </div>
  <div id="loginSection" style="display: none;">
    <video id="videoLogin" autoplay muted></video>
    <div id="messageLogin"></div>
    <div id="loginHistoryContainer">
      <h2>Login History</h2>
      <ul id="loginHistoryList">
        <li>Loading login history...</li>
      </ul>
    </div>
  </div>
</div>
<script>
const videoRegister = document.getElementById('videoRegister');
const videoLogin = document.getElementById('videoLogin');
const registerSection = document.getElementById('registerSection');
const loginSection = document.getElementById('loginSection');
const captureRegister = document.getElementById('captureRegister');
const messageRegister = document.getElementById('messageRegister');
const messageLogin = document.getElementById('messageLogin');
const usernameInput = document.getElementById('username');
const registerBtn = document.getElementById('registerBtn');
const loginBtn = document.getElementById('loginBtn');
const loginHistoryList = document.getElementById('loginHistoryList');

let loginInterval = null;

function showMessage(element, msg, color='white') {
  element.innerText = msg;
  element.style.color = color;
}

function startVideoStream(videoElement) {
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({video: true})
    .then(stream => {
      videoElement.srcObject = stream;
    })
    .catch(err => {
      alert('Error accessing webcam: ' + err);
    });
  } else {
    alert('getUserMedia not supported in this browser.');
  }
}

function captureFrame(videoElement) {
  const canvas = document.createElement('canvas');
  canvas.width = videoElement.videoWidth || 320;
  canvas.height = videoElement.videoHeight || 240;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg');
}

async function registerUser() {
  const username = usernameInput.value.trim();
  if (!username) {
    showMessage(messageRegister, 'Please enter a username.', '#ff7070');
    return;
  }
  showMessage(messageRegister, 'Capturing face and registering...', '#ffd600');
  const imgData = captureFrame(videoRegister);
  try {
    const resp = await fetch('/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username, image: imgData})
    });
    const result = await resp.json();
    if(result.success){
      showMessage(messageRegister, 'User "' + username + '" registered successfully!', '#7fff7f');
      usernameInput.value = '';
    } else {
      showMessage(messageRegister, 'Error: ' + result.message, '#ff7070');
    }
  } catch (error) {
    showMessage(messageRegister, 'Error: ' + error.message, '#ff7070');
  }
}

async function refreshLoginHistory() {
  try {
    const resp = await fetch('/login-history');
    const data = await resp.json();
    if(data.success) {
      const history = data.history;
      if(history.length === 0) {
        loginHistoryList.innerHTML = '<li><i>No login history yet</i></li>';
        return;
      }
      loginHistoryList.innerHTML = '';
      history.slice().reverse().forEach(entry => {
        const li = document.createElement('li');
        const timeStr = new Date(entry.timestamp).toLocaleString();
        li.textContent = timeStr + ' - ' + entry.username;
        loginHistoryList.appendChild(li);
      });
    } else {
      loginHistoryList.innerHTML = '<li>Error loading history</li>';
    }
  } catch (error) {
    loginHistoryList.innerHTML = '<li>Error fetching login history</li>';
  }
}

async function loginUser() {
  showMessage(messageLogin, 'Detecting face... Please keep your face visible.', '#ffd600');
  const imgData = captureFrame(videoLogin);
  try {
    const resp = await fetch('/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({image: imgData})
    });
    const result = await resp.json();
    if(result.success){
      showMessage(messageLogin, '');
      showMessage(messageLogin, 'Welcome, ' + result.username + '! Login successful.', '#7fff7f');
      await refreshLoginHistory();
    } else {
      showMessage(messageLogin, 'Face not recognized. Try again.', '#ff7070');
    }
  } catch (error) {
    showMessage(messageLogin, 'Error: ' + error.message, '#ff7070');
  }
}

registerBtn.addEventListener('click', () => {
  registerSection.style.display = 'block';
  loginSection.style.display = 'none';
  registerBtn.classList.add('active');
  loginBtn.classList.remove('active');
  clearInterval(loginInterval);
});

loginBtn.addEventListener('click', () => {
  loginSection.style.display = 'block';
  registerSection.style.display = 'none';
  loginBtn.classList.add('active');
  registerBtn.classList.remove('active');

  if(loginInterval) {
    clearInterval(loginInterval);
  }
  refreshLoginHistory();
  // Capture and send frames for login every 2 seconds
  loginInterval = setInterval(loginUser, 2000);
});

captureRegister.addEventListener('click', registerUser);

startVideoStream(videoRegister);
startVideoStream(videoLogin);

</script>
</body>
</html>
'''

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    img_b64 = data.get('image', '')

    if not username:
        return jsonify({'success': False, 'message': 'Username is required'})

    if not img_b64:
        return jsonify({'success': False, 'message': 'Image data is required'})

    global users
    if username.lower() in (u.lower() for u in users.keys()):
        return jsonify({'success': False, 'message': 'Username already exists'})

    try:
        image = base64_to_image(img_b64)
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image data'})

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return jsonify({'success': False, 'message': 'No face detected. Please try again with clearer face image.'})
    elif len(encodings) > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected. Please ensure only your face is visible.'})

    users[username] = encodings[0]
    save_users(users)

    return jsonify({'success': True, 'message': 'User registered successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    img_b64 = data.get('image', '')

    if not img_b64:
        return jsonify({'success': False, 'message': 'Image data required'})

    try:
        image = base64_to_image(img_b64)
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image data'})

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return jsonify({'success': False, 'message': 'No face detected'})

    input_encoding = encodings[0]

    if not users:
        return jsonify({'success': False, 'message': 'No registered users'})

    usernames = list(users.keys())
    all_encodings = np.array(list(users.values()))

    distances = face_recognition.face_distance(all_encodings, input_encoding)
    if len(distances) == 0:
        return jsonify({'success': False, 'message': 'No faces stored'})

    min_dist_idx = np.argmin(distances)
    min_dist = distances[min_dist_idx]

    if min_dist < 0.55:
        matched_user = usernames[min_dist_idx]
        # Append login event to history
        global login_history
        login_history.append({'username': matched_user, 'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'})
        # Keep history size manageable (e.g., last 100 events)
        login_history = login_history[-100:]
        save_login_history(login_history)
        return jsonify({'success': True, 'username': matched_user})

    return jsonify({'success': False, 'message': 'Face not recognized'})

@app.route('/login-history')
def login_history_route():
    global login_history
    return jsonify({'success': True, 'history': login_history})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


