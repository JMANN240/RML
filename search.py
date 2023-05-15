def search(cur, term):
	if term is None:
		return []
	res = cur.execute('SELECT *, recipes.id AS recipe_id, users.id AS user_id FROM recipes INNER JOIN users ON recipes.user_id=users.id WHERE name LIKE ?', (f"%{term}%",))
	name_matched_recipes = res.fetchall()
	res = cur.execute('SELECT * FROM recipes INNER JOIN recipe_ingredients ON recipes.id=recipe_ingredients.recipe_id WHERE ingredient LIKE ?', (f"%{term}%",))
	ingredient_matches = res.fetchall()
	res = cur.execute('SELECT * FROM recipes INNER JOIN recipe_steps ON recipes.id=recipe_steps.recipe_id WHERE step LIKE ?', (f"%{term}%",))
	step_matches = res.fetchall()

	name_match_ids = [match['recipe_id'] for match in name_matched_recipes]
	ingredient_match_ids = [match['recipe_id'] for match in ingredient_matches if match['recipe_id'] not in name_match_ids]
	step_match_ids = [match['recipe_id'] for match in step_matches if match['recipe_id'] not in name_match_ids + ingredient_match_ids]

	res = cur.execute(f"SELECT *, recipes.id AS recipe_id, users.id AS user_id FROM recipes INNER JOIN users ON recipes.user_id=users.id WHERE recipes.id IN ({','.join('?'*len(ingredient_match_ids))})", ingredient_match_ids)
	ingredient_matched_recipes = res.fetchall()

	res = cur.execute(f"SELECT *, recipes.id AS recipe_id, users.id AS user_id FROM recipes INNER JOIN users ON recipes.user_id=users.id WHERE recipes.id IN ({','.join('?'*len(step_match_ids))})", step_match_ids)
	step_matched_recipes = res.fetchall()

	return name_matched_recipes + ingredient_matched_recipes + step_matched_recipes