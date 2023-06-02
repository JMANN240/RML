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
		return dict(user_id=None, user_authority=0)
	con, cur = get_db()
	res = cur.execute('SELECT * FROM sessions INNER JOIN users ON sessions.user_id=users.id WHERE session_id=?', (request.cookies.get('session'),))
	session = res.fetchone()
	if session is None:
		return dict(user_id=None, user_authority=0)
	return dict(user_id=session.get('user_id'), user_authority=session.get('authority'))

@app.route('/')
def index():
	con, cur = get_db()
	res = cur.execute('SELECT * FROM recipes ORDER BY id DESC LIMIT 10')
	recipes = res.fetchall()
	return render_template('index.html', recipes=recipes, title='Home')

@app.route('/profile/<profile_user_id>')
def profile(profile_user_id):
	con, cur = get_db()
	if request.cookies.get('session') is None:
		logged_in_user_id = None
	else:
		res = cur.execute('SELECT * FROM sessions INNER JOIN users ON sessions.user_id=users.id WHERE session_id=?', (request.cookies.get('session'),))
		session = res.fetchone()
		if session is None:
			logged_in_user_id = None
		else:
			logged_in_user_id = session.get('user_id')
	res = cur.execute('SELECT * FROM users WHERE id=?', (profile_user_id,))
	profile_user = res.fetchone()
	res = cur.execute('SELECT * FROM recipes WHERE user_id=? ORDER BY id DESC', (profile_user_id,))
	user_recipes = res.fetchall()
	res = cur.execute('SELECT * FROM user_favorites INNER JOIN recipes ON recipes.id == user_favorites.recipe_id WHERE user_favorites.user_id=? ORDER BY name', (profile_user_id,))
	favorite_recipes = res.fetchall()

	return render_template('profile.html', profile_user=profile_user, user_recipes=user_recipes, favorite_recipes=favorite_recipes, title=f"{profile_user['username']}'s Profile", logged_in_user_id=logged_in_user_id)

@app.route('/search', methods=['GET', 'POST'])
def search():
	if request.method == 'GET':
		con, cur = get_db()
		term = request.args.get('search')
		results = search_algorithm.search(cur, term)
		return render_template('search.html', results=results, term=term, title='Search')
	
	elif request.method == 'POST':
		term = request.form.get('term')
		if term is None:
			flash("Search term cannot be empty", 'error')
			return redirect(url_for('index'))
		return redirect(url_for('search', search=term))

@app.route('/recipe/<recipe_id>')
def recipe(recipe_id):
	con, cur = get_db()
	res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
	recipe = res.fetchone()
	if recipe is None:
		flash(f"Recipe with ID {recipe_id} not found", 'error')
		return redirect(url_for('index'))
	res = cur.execute('SELECT * FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
	ingredients = res.fetchall()
	res = cur.execute('SELECT * FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
	steps = res.fetchall()

	if request.cookies.get('session') is None:
		is_user_favorite = False
	else:
		res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (request.cookies.get('session'),))
		session = res.fetchone()
		if session is None:
			is_user_favorite = False
		else:
			user_id = session.get('user_id')
			res = cur.execute('SELECT * FROM user_favorites WHERE recipe_id=? AND user_id=?', (recipe_id, user_id))
			favorite = res.fetchone()
			is_user_favorite = favorite is not None
	
	res = cur.execute('SELECT * FROM users WHERE id=?', (recipe['user_id'],))
	author = res.fetchone()

	has_additional_info = any([info != '' for info in (recipe['calories'], recipe['protein'], recipe['total_fat'], recipe['saturated_fat'], recipe['trans_fat'], recipe['cholesterol'], recipe['carbohydrates'], recipe['sugar'], recipe['fiber'], recipe['sodium'])])
	
	return render_template('recipe.html', recipe=recipe, ingredients=ingredients, steps=steps, title=recipe.get('name'), is_user_favorite=is_user_favorite, author=author, has_additional_info=has_additional_info)

@app.route('/recipe/<recipe_id>/favorite')
@requires_login
def toggle_recipe_favorite(recipe_id):
	user_id = request.user_id
	con, cur = get_db()
	res = cur.execute('SELECT * FROM user_favorites WHERE recipe_id=? AND user_id=?', (recipe_id, user_id))
	favorite = res.fetchone()
	if favorite is None:
		cur.execute('INSERT INTO user_favorites (recipe_id, user_id) VALUES (?, ?)', (recipe_id, user_id))
	else:
		cur.execute('DELETE FROM user_favorites WHERE recipe_id=? AND user_id=?', (recipe_id, user_id))
	con.commit()
	return redirect(url_for('recipe', recipe_id=recipe_id))

@app.route('/recipe/create', methods=['GET', 'POST'])
@requires_login
def recipe_create():
	if request.method == 'GET':
		return render_template('recipe_create.html', title='Create Recipe')

	elif request.method == 'POST':
		user_id = request.user_id
		recipe_name = request.form.get('recipe-name')
		result = request.form.get('result')
		recipe_ingredients_pre = request.form.get('ingredients')
		recipe_steps_pre = request.form.get('steps')

		if recipe_name is None or recipe_name == '':
			flash("Recipe name cannot be empty", 'error')
			return redirect(url_for('recipe_create'))

		if result is None or result == '':
			flash("Result cannot be empty", 'error')
			return redirect(url_for('recipe_create'))

		if recipe_ingredients_pre is None or recipe_ingredients_pre == []:
			flash("Recipe ingredients cannot be empty", 'error')
			return redirect(url_for('recipe_create'))

		if recipe_steps_pre is None or recipe_steps_pre == []:
			flash("Recipe steps cannot be empty", 'error')
			return redirect(url_for('recipe_create'))

		recipe_ingredients = recipe_ingredients_pre.split('\n')
		recipe_steps = recipe_steps_pre.split('\n')

		calories = request.form.get('calories')
		protein = request.form.get('protein')
		total_fat = request.form.get('total-fat')
		saturated_fat = request.form.get('saturated-fat')
		trans_fat = request.form.get('trans-fat')
		cholesterol = request.form.get('cholesterol')
		carbohydrates = request.form.get('carbohydrates')
		sugar = request.form.get('sugar')
		fiber = request.form.get('fiber')
		sodium = request.form.get('sodium')

		con, cur = get_db()
		cur.execute('INSERT INTO recipes (name, user_id, result, calories, protein, total_fat, saturated_fat, trans_fat, cholesterol, carbohydrates, sugar, fiber, sodium) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (recipe_name, user_id, result, calories, protein, total_fat, saturated_fat, trans_fat, cholesterol, carbohydrates, sugar, fiber, sodium))
		res = cur.execute("SELECT * FROM recipes ORDER BY id DESC LIMIT 1")
		recipe = res.fetchone()
		cur.executemany('INSERT INTO recipe_ingredients (recipe_id, ingredient) VALUES (?, ?)', [(recipe.get('id'), ingredient) for ingredient in recipe_ingredients])
		cur.executemany('INSERT INTO recipe_steps (recipe_id, step) VALUES (?, ?)', [(recipe.get('id'), step) for step in recipe_steps])
		con.commit()

		return redirect(url_for('recipe', recipe_id=recipe.get('id')))

@app.route('/recipe/<recipe_id>/edit', methods=['GET', 'POST'])
@requires_login
def recipe_edit(recipe_id):
	if request.method == 'GET':
		con, cur = get_db()
		res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
		recipe = res.fetchone()
		if recipe is None:
			flash(f"Recipe with ID {recipe_id} not found", 'error')
			return redirect(url_for('index'))
		if recipe['user_id'] != request.user_id and request.user_authority == 0:
			flash(f"You do not have permission to edit recipe with ID {recipe_id}.", 'error')
			return redirect(url_for('index'))
		res = cur.execute('SELECT * FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
		ingredients = res.fetchall()
		ingredients = '\n'.join([ingredient.get('ingredient') for ingredient in ingredients])
		res = cur.execute('SELECT * FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
		steps = res.fetchall()
		steps = '\n'.join([step.get('step') for step in steps])
		return render_template('recipe_edit.html', recipe_id=recipe_id, recipe=recipe, ingredients=ingredients, steps=steps, title='Edit Recipe')

	elif request.method == 'POST':
		recipe_id = request.form.get('recipe-id')
		recipe_name = request.form.get('recipe-name')
		result = request.form.get('result')
		recipe_ingredients_pre = request.form.get('ingredients')
		recipe_steps_pre = request.form.get('steps')

		if recipe_id is None or recipe_id == '':
			flash("Recipe ID cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		if recipe_name is None or recipe_name == '':
			flash("Recipe name cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		if result is None or result == '':
			flash("Result cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		if recipe_ingredients_pre is None or recipe_ingredients_pre == []:
			flash("Recipe ingredients cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		if recipe_steps_pre is None or recipe_steps_pre == []:
			flash("Recipe steps cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		recipe_ingredients = recipe_ingredients_pre.split('\n')
		recipe_steps = recipe_steps_pre.split('\n')

		calories = request.form.get('calories')
		protein = request.form.get('protein')
		total_fat = request.form.get('total-fat')
		saturated_fat = request.form.get('saturated-fat')
		trans_fat = request.form.get('trans-fat')
		cholesterol = request.form.get('cholesterol')
		carbohydrates = request.form.get('carbohydrates')
		sugar = request.form.get('sugar')
		fiber = request.form.get('fiber')
		sodium = request.form.get('sodium')

		con, cur = get_db()
		res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
		recipe = res.fetchone()
		if recipe is None:
			flash(f"Recipe with ID {recipe_id} not found", 'error')
			return redirect(url_for('index'))
		if recipe['user_id'] != request.user_id and request.user_authority == 0:
			flash(f"You do not have permission to edit recipe with ID {recipe_id}.", 'error')
			return redirect(url_for('index'))
		
		cur.execute('UPDATE recipes SET name=?, result=?, calories=?, protein=?, total_fat=?, saturated_fat=?, trans_fat=?, cholesterol=?, carbohydrates=?, sugar=?, fiber=?, sodium=? WHERE id=?', (recipe_name, result, calories, protein, total_fat, saturated_fat, trans_fat, cholesterol, carbohydrates, sugar, fiber, sodium, recipe_id))
		cur.execute('DELETE FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
		cur.execute('DELETE FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
		cur.executemany('INSERT INTO recipe_ingredients (recipe_id, ingredient) VALUES (?, ?)', [(recipe_id, ingredient) for ingredient in recipe_ingredients])
		cur.executemany('INSERT INTO recipe_steps (recipe_id, step) VALUES (?, ?)', [(recipe_id, step) for step in recipe_steps])
		con.commit()

		return redirect(url_for('recipe', recipe_id=recipe_id))

@app.route('/recipe/<recipe_id>/delete', methods=['GET', 'POST'])
@requires_login
def recipe_delete(recipe_id):
	if request.method == 'GET':
		con, cur = get_db()
		res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
		recipe = res.fetchone()
		if recipe is None:
			flash(f"Recipe with ID {recipe_id} not found", 'error')
			return redirect(url_for('index'))
		if recipe['user_id'] != request.user_id and request.user_authority == 0:
			flash(f"You do not have permission to edit recipe with ID {recipe_id}.", 'error')
			return redirect(url_for('index'))
		return render_template('recipe_delete.html', recipe_id=recipe_id, recipe=recipe, title='Delete Recipe')

	elif request.method == 'POST':
		recipe_id = request.form.get('recipe-id')

		if recipe_id is None:
			flash("Recipe ID cannot be empty", 'error')
			return redirect(url_for('recipe_edit'))

		con, cur = get_db()
		res = cur.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,))
		recipe = res.fetchone()
		recipe_user_id = recipe['user_id']
		if recipe is None:
			flash(f"Recipe with ID {recipe_id} not found", 'error')
			return redirect(url_for('index'))
		if recipe['user_id'] != request.user_id and request.user_authority == 0:
			flash(f"You do not have permission to edit recipe with ID {recipe_id}.", 'error')
			return redirect(url_for('index'))
		cur.execute('DELETE FROM recipe_ingredients WHERE recipe_id=?', (recipe_id,))
		cur.execute('DELETE FROM recipe_steps WHERE recipe_id=?', (recipe_id,))
		cur.execute('DELETE FROM user_favorites WHERE recipe_id=?', (recipe_id,))
		cur.execute('DELETE FROM recipes WHERE id=?', (recipe_id,))
		con.commit()

		return redirect(url_for('profile', profile_user_id=recipe_user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'GET':
		return render_template('login.html', title='Login')
	
	elif request.method == 'POST':
		con, cur = get_db()
		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form.get('username'),))
		user = res.fetchone()
		if user is None:
			flash("Username does not exist", 'error')
			return redirect(url_for('login'))

		hasher = hashlib.sha512()
		hasher.update(bytes(request.form.get('password'), 'ascii'))
		passhash = hasher.hexdigest()

		if passhash != user.get('passhash'):
			flash("Incorrect password", 'error')
			return redirect(url_for('login'))
		
		is_new_session_id = False
		while not is_new_session_id:
			session_id = os.urandom(64).hex()
			res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (session_id,))
			if len(res.fetchall()) == 0:
				is_new_session_id = True
		
		user_id = user.get('id')

		cur.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
		cur.execute('INSERT INTO sessions (session_id, user_id, created) VALUES (?, ?, ?)', (session_id, user_id, int(time.time())))
		con.commit()
		
		res = make_response(redirect(url_for('index')))
		res.set_cookie('session', session_id, max_age=60*60*24*365*10)
		return res

@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'GET':
		return render_template('register.html', title='Register')
	
	elif request.method == 'POST':
		if request.form.get('username') == "":
			flash("Username cannot be empty", 'error')
			return redirect(url_for('register'))

		if request.form.get('password') == "":
			flash("Password cannot be empty", 'error')
			return redirect(url_for('register'))

		if request.form.get('password') != request.form.get('confirm-password'):
			flash("Passwords do not match", 'error')
			return redirect(url_for('register'))
		
		con, cur = get_db()
		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form.get('username'),))
		user = res.fetchone()
		if user is not None:
			flash("Username already exists", 'error')
			return redirect(url_for('register'))

		hasher = hashlib.sha512()
		hasher.update(bytes(request.form.get('password'), 'ascii'))
		passhash = hasher.hexdigest()
		
		cur.execute('INSERT INTO users (username, passhash) VALUES (?, ?)', (request.form.get('username'), passhash))
		con.commit()

		res = cur.execute('SELECT * FROM users WHERE username=?', (request.form.get('username'),))
		user = res.fetchone()
		
		is_new_session_id = False
		while not is_new_session_id:
			session_id = os.urandom(64).hex()
			res = cur.execute('SELECT * FROM sessions WHERE session_id=?', (session_id,))
			if len(res.fetchall()) == 0:
				is_new_session_id = True
		user_id = user.get('id')

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