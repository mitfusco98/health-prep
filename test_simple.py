#!/usr/bin/env python3
"""
Simple Flask app test to isolate the core issue
"""

from flask import Flask, render_template, session, redirect, url_for, request
import os

# Create minimal Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "test-secret-key")

# Simple login check
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    """Simple home page"""
    return "<h1>Healthcare App Running</h1><p>Server is working correctly!</p><p><a href='/login'>Login</a></p>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['user_id'] = 1
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials. Try admin/admin123"
    
    return """
    <form method="post">
        <h2>Login</h2>
        <p>Username: <input name="username" value="admin"></p>
        <p>Password: <input name="password" type="password" value="admin123"></p>
        <p><input type="submit" value="Login"></p>
    </form>
    """

@app.route('/dashboard')
@login_required
def dashboard():
    """Simple dashboard"""
    return f"<h1>Welcome {session.get('username')}</h1><p>App is working!</p><p><a href='/logout'>Logout</a></p>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting simple test server...")
    app.run(host='0.0.0.0', port=5001, debug=True)