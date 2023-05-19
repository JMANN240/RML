from functools import wraps
from flask import make_response, redirect, request, url_for
import sqlite3

def dict_factory(cursor, row):
	d = {}
	for i, col in enumerate(cursor.description):
		d[col[0]] = row[i]
	return d

def get_db():
	con = sqlite3.connect('database.db')
	con.row_factory = dict_factory
	cur = con.cursor()
	return con, cur

def requires_login(f):
	@wraps(f)
	def inner(*args, **kwargs):
		if request.cookies.get('session') is None:
			return redirect(url_for('login'))
		con, cur = get_db()
		res = cur.execute('SELECT * FROM sessions INNER JOIN users ON sessions.user_id=users.id WHERE session_id=?', (request.cookies.get('session'),))
		session = res.fetchone()
		if session is None:
			return redirect(url_for('login'))
		setattr(request, 'user_id', session['user_id'])
		setattr(request, 'user_authority', session['authority'])
		return f(*args, **kwargs)
	return inner