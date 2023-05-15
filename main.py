from flask import Flask, render_template, request, redirect, make_response, flash, url_for
import os
from util import get_db, requires_login
import hashlib
import time

app = Flask(__name__)
app.secret_key = os.urandom(64)

@app.context_processor
def inject_user():
	if request.cookies.get('session') is None:
		return dict(user_id=None)
	con, cur = get_db()
	res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (request.cookies.get('session'),))
	session = res.fetchone()
	if session is None:
		return dict(user_id=None)
	return dict(user_id=session['user_id'])

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/recipe')
def recipe():
	return render_template('recipe.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		return render_template('login.html')
	
	elif request.method == 'POST':
		con, cur = get_db()
		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form['username'],))
		user = res.fetchone()
		if user is None:
			flash("Username does not exist", 'error')
			return redirect(url_for('login'))

		hasher = hashlib.sha512()
		hasher.update(bytes(request.form['password'], 'ascii'))
		passhash = hasher.hexdigest()

		if passhash != user['passhash']:
			flash("Incorrect password", 'error')
			return redirect(url_for('login'))
		
		session_id = os.urandom(64).hex()
		user_id = user['id']

		cur.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
		cur.execute('INSERT INTO sessions (session_id, user_id, created) VALUES (?, ?, ?)', (session_id, user_id, int(time.time())))
		con.commit()
		
		res = make_response(redirect(url_for('index')))
		res.set_cookie('session', session_id, max_age=60*60*24*365*10)
		return res

@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'GET':
		return render_template('register.html')
	
	elif request.method == 'POST':
		if request.form['password'] != request.form['confirm-password']:
			flash("Passwords do not match", 'error')
			return redirect(url_for('login'))
		
		con, cur = get_db()
		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form['username'],))
		user = res.fetchone()
		if user is not None:
			flash("Username already exists", 'error')
			return redirect(url_for('login'))

		hasher = hashlib.sha512()
		hasher.update(bytes(request.form['password'], 'ascii'))
		passhash = hasher.hexdigest()
		
		cur.execute('INSERT INTO users (username, passhash) VALUES (?, ?)', (request.form['username'], passhash))
		con.commit()

		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form['username'],))
		user = res.fetchone()
		
		session_id = os.urandom(64).hex()
		user_id = user['id']

		cur.execute('INSERT INTO sessions (session_id, user_id, created) VALUES (?, ?, ?)', (session_id, user_id, int(time.time())))
		con.commit()
		
		res = make_response(redirect(url_for('index')))
		res.set_cookie('session', session_id, max_age=60*60*24*365*10)
		return res

@app.route('/logout')
@requires_login
def logout():
	con, cur = get_db()
	cur.execute('DELETE FROM sessions WHERE user_id=?', (request.user_id,))
	con.commit()

	res = make_response(redirect(url_for('login')))
	res.set_cookie('session', '', expires=0)
	return res


if __name__ == '__main__':
	app.run(debug=True)