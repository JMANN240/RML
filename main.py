from flask import Flask, render_template, request, redirect, make_response, flash, url_for
import os
from util import get_db, requires_login
import hashlib
import time
import search as search_algorithm

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
	con, cur = get_db()
	res = cur.execute('SELECT * FROM recipes ORDER BY id DESC LIMIT 10')
	recipes = res.fetchall()
	return render_template('index.html', recipes=recipes)

@app.route('/profile')
@requires_login
def profile():
	con, cur = get_db()
	res = cur.execute('SELECT * FROM users WHERE id=?', (request.user_id,))
	user = res.fetchone()
	res = cur.execute('SELECT * FROM recipes WHERE user_id=?', (request.user_id,))
	user_recipes = res.fetchall()
	return render_template('profile.html', user=user, user_recipes=user_recipes)

@app.route('/search', methods=['GET', 'POST'])
def search():
	if request.method == 'GET':
		con, cur = get_db()
		term = request.args.get('search')
		results = search_algorithm.search(cur, term)
		return render_template('search.html', results=results, term=term)
	
	elif request.method == 'POST':
		return redirect(url_for('search', search=request.form['term']))

@app.route('/recipe/<recipe_id>')
def recipe(recipe_id):
	con, cur = get_db()
	res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
	recipe = res.fetchone()
	res = cur.execute('SELECT * FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
	ingredients = res.fetchall()
	res = cur.execute('SELECT * FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
	steps = res.fetchall()
	return render_template('recipe.html', recipe=recipe, ingredients=ingredients, steps=steps)

@app.route('/recipe/create', methods=['GET', 'POST'])
@requires_login
def recipe_create():
	if request.method == 'GET':
		return render_template('recipe_create.html')

	elif request.method == 'POST':
		user_id = request.user_id
		recipe_name = request.form['recipe-name']
		recipe_ingredients = request.form['ingredients'].split('\n')
		recipe_steps = request.form['steps'].split('\n')

		con, cur = get_db()
		cur.execute('INSERT INTO recipes (name, user_id) VALUES (?, ?)', (recipe_name, user_id))
		res = cur.execute("SELECT * FROM recipes ORDER BY id DESC LIMIT 1")
		recipe = res.fetchone()
		cur.executemany('INSERT INTO recipe_ingredients (recipe_id, ingredient) VALUES (?, ?)', [(recipe['id'], ingredient) for ingredient in recipe_ingredients])
		cur.executemany('INSERT INTO recipe_steps (recipe_id, step) VALUES (?, ?)', [(recipe['id'], step) for step in recipe_steps])
		con.commit()

		return redirect(url_for('recipe', recipe_id=recipe['id']))

@app.route('/recipe/<recipe_id>/edit', methods=['GET', 'POST'])
@requires_login
def recipe_edit(recipe_id):
	if request.method == 'GET':
		con, cur = get_db()
		res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
		recipe = res.fetchone()
		res = cur.execute('SELECT * FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
		ingredients = res.fetchall()
		ingredients = '\n'.join([ingredient['ingredient'] for ingredient in ingredients])
		res = cur.execute('SELECT * FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
		steps = res.fetchall()
		steps = '\n'.join([step['step'] for step in steps])
		return render_template('recipe_edit.html', recipe_id=recipe_id, recipe=recipe, ingredients=ingredients, steps=steps)

	elif request.method == 'POST':
		user_id = request.user_id
		recipe_id = request.form['recipe-id']
		recipe_name = request.form['recipe-name']
		recipe_ingredients = request.form['ingredients'].split('\n')
		recipe_steps = request.form['steps'].split('\n')

		con, cur = get_db()
		cur.execute('UPDATE recipes SET name=? WHERE id=?', (recipe_name, recipe_id))
		cur.execute('DELETE FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
		cur.execute('DELETE FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
		cur.executemany('INSERT INTO recipe_ingredients (recipe_id, ingredient) VALUES (?, ?)', [(recipe_id, ingredient) for ingredient in recipe_ingredients])
		cur.executemany('INSERT INTO recipe_steps (recipe_id, step) VALUES (?, ?)', [(recipe_id, step) for step in recipe_steps])
		con.commit()

		return redirect(url_for('recipe', recipe_id=recipe_id))

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
		
		is_new_session_id = False
		while not is_new_session_id:
			session_id = os.urandom(64).hex()
			res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (session_id,))
			if len(res.fetchall()) == 0:
				is_new_session_id = True
		
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
		
		is_new_session_id = False
		while not is_new_session_id:
			session_id = os.urandom(64).hex()
			res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (session_id,))
			if len(res.fetchall()) == 0:
				is_new_session_id = True
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