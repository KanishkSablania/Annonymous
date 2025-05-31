from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, join_room, leave_room, send, emit
spam_cache = {}
from flask_session import Session
from datetime import datetime, timedelta
import random
import string
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)

rooms = {}
user_sessions = {}

aliases = ['CuriousFox', 'BraveLion', 'GentleOtter', 'MellowPine', 'ShyStar', 'CalmStorm', 'SilentRiver']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    username = request.form['username']
    room = request.form['room']
    session['username'] = username
    session['room'] = room
    return render_template('chat.html', username=username, room=room)

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    if room not in rooms:
        rooms[room] = []
    rooms[room].append(username)
    emit("user_count", {"count": len(set(rooms[room]))}, to=room)
    send(f"{username} joined the room.", to=room)

@socketio.on('message')
def handle_message(data):
    username = data['username']
    room = data['room']
    message = data['message']
    now = datetime.now()
    last_sent = user_sessions.get(username, now - timedelta(seconds=5))
    if (now - last_sent).total_seconds() >= 2:
        user_sessions[username] = now

        user_ip = request.remote_addr
        key = f"{user_ip}:{room}"
        last_message = spam_cache.get(key, "")
        if message == last_message:
            print(f"[ADMIN ALERT] Possible spam from IP {user_ip}, message: {message}")
            emit("message", "[ANTI-SPAM] Repeated messages are blocked.", to=request.sid)
            return
        spam_cache[key] = message

        send(f"{username}: {message}", to=room)

@socketio.on('typing')
def handle_typing(data):
    emit("typing", {"username": data['username']}, to=data['room'], include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    emit("stop_typing", {"username": data['username']}, to=data['room'], include_self=False)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

