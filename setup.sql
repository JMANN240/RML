CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    passhash TEXT NOT NULL,
	authority INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
	session_id TEXT NOT NULL,
	user_id INTEGER NOT NULL,
	created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
	id INTEGER PRIMARY KEY,
	name TEXT NOT NULL,
	user_id INTEGER NOT NULL,
	result TEXT NOT NULL,
	calories INTEGER DEFAULT '',
	protein INTEGER DEFAULT '',
	total_fat INTEGER DEFAULT '',
	saturated_fat INTEGER DEFAULT '',
	trans_fat INTEGER DEFAULT '',
	cholesterol INTEGER DEFAULT '',
	carbohydrates INTEGER DEFAULT '',
	sugar INTEGER DEFAULT '',
	fiber INTEGER DEFAULT '',
	sodium INTEGER DEFAULT '',
	FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
	recipe_id INTEGER NOT NULL,
	ingredient TEXT NOT NULL,
	FOREIGN KEY (recipe_id) REFERENCES recipes (id)
);

CREATE TABLE IF NOT EXISTS recipe_steps (
	recipe_id INTEGER NOT NULL,
	step TEXT NOT NULL,
	FOREIGN KEY (recipe_id) REFERENCES recipes (id)
);

CREATE TABLE IF NOT EXISTS user_favorites (
	user_id INTEGER NOT NULL,
	recipe_id INTEGER NOT NULL,
	FOREIGN KEY (user_id) REFERENCES users (id),
	FOREIGN KEY (recipe_id) REFERENCES recipes (id)
);