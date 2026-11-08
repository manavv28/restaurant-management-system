-- Fresh Supabase/PostgreSQL database. Backend-only access; custom API auth.

CREATE TABLE users (
	id SERIAL NOT NULL,
	email VARCHAR(254) NOT NULL,
	name VARCHAR(80) NOT NULL,
	password_hash TEXT NOT NULL,
	role VARCHAR(20) NOT NULL,
	consent BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
)

;


CREATE TABLE restaurants (
	id SERIAL NOT NULL,
	owner_id INTEGER,
	name VARCHAR(150) NOT NULL,
	address TEXT NOT NULL,
	area VARCHAR(80) NOT NULL,
	pin_code VARCHAR(6) NOT NULL,
	latitude FLOAT NOT NULL,
	longitude FLOAT NOT NULL,
	cuisine VARCHAR(100) NOT NULL,
	phone VARCHAR(30) NOT NULL,
	website TEXT NOT NULL,
	rating FLOAT,
	opening_hours TEXT NOT NULL,
	price_range VARCHAR(40) NOT NULL,
	source TEXT NOT NULL,
	source_id VARCHAR(200),
	sample BOOLEAN NOT NULL,
	updated_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(owner_id) REFERENCES users (id),
	UNIQUE (source_id),
	CONSTRAINT mumbai_coordinates CHECK (latitude BETWEEN 18.85 AND 19.35 AND longitude BETWEEN 72.75 AND 73.05)
)

;

CREATE INDEX ix_restaurants_area ON restaurants (area);

CREATE INDEX ix_restaurants_cuisine ON restaurants (cuisine);

CREATE INDEX ix_restaurants_owner_id ON restaurants (owner_id);


CREATE TABLE searches (
	id SERIAL NOT NULL,
	user_id INTEGER,
	query TEXT NOT NULL,
	cuisine VARCHAR(100),
	dish VARCHAR(150),
	budget INTEGER NOT NULL,
	area VARCHAR(80) NOT NULL,
	results INTEGER NOT NULL,
	trace TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE INDEX ix_searches_user_id ON searches (user_id);


CREATE TABLE preferences (
	user_id INTEGER NOT NULL,
	preferred_cuisine VARCHAR(100) NOT NULL,
	PRIMARY KEY (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;


CREATE TABLE menu_items (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	name VARCHAR(150) NOT NULL,
	category VARCHAR(80) NOT NULL,
	cuisine VARCHAR(100) NOT NULL,
	price_paise INTEGER NOT NULL,
	description TEXT NOT NULL,
	available BOOLEAN NOT NULL,
	source TEXT NOT NULL,
	verified_at VARCHAR(40),
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id),
	CONSTRAINT positive_menu_price CHECK (price_paise > 0)
)

;

CREATE INDEX ix_menu_items_name ON menu_items (name);

CREATE INDEX ix_menu_items_restaurant_id ON menu_items (restaurant_id);


CREATE TABLE favourites (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	menu_item_id INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, restaurant_id, menu_item_id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)

;

CREATE INDEX ix_favourites_user_id ON favourites (user_id);


CREATE TABLE campaigns (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	title VARCHAR(100) NOT NULL,
	percent INTEGER NOT NULL,
	min_searches INTEGER NOT NULL,
	min_spend_paise INTEGER NOT NULL,
	min_visits INTEGER NOT NULL,
	min_order_paise INTEGER NOT NULL,
	max_discount_paise INTEGER NOT NULL,
	redemption_limit INTEGER NOT NULL,
	starts_at VARCHAR(40) NOT NULL,
	ends_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id),
	CONSTRAINT valid_campaign CHECK (percent BETWEEN 1 AND 80 AND max_discount_paise > 0 AND redemption_limit > 0)
)

;

CREATE INDEX ix_campaigns_restaurant_id ON campaigns (restaurant_id);


CREATE TABLE transactions (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	reference VARCHAR(100) NOT NULL,
	amount_paise INTEGER NOT NULL,
	simulated BOOLEAN NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id),
	UNIQUE (reference),
	CONSTRAINT positive_transaction CHECK (amount_paise > 0)
)

;

CREATE INDEX ix_transactions_user_id ON transactions (user_id);


CREATE TABLE interactions (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)

;

CREATE INDEX ix_interactions_restaurant_id ON interactions (restaurant_id);


CREATE TABLE ingestion_logs (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	source TEXT NOT NULL,
	trace TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id)
)

;

CREATE INDEX ix_ingestion_logs_restaurant_id ON ingestion_logs (restaurant_id);


CREATE TABLE redemptions (
	id SERIAL NOT NULL,
	user_id INTEGER NOT NULL,
	campaign_id INTEGER NOT NULL,
	sequence INTEGER NOT NULL,
	order_paise INTEGER NOT NULL,
	discount_paise INTEGER NOT NULL,
	audit TEXT NOT NULL,
	created_at VARCHAR(40) NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id, campaign_id, sequence),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(campaign_id) REFERENCES campaigns (id),
	CONSTRAINT valid_redemption CHECK (discount_paise >= 0 AND discount_paise <= order_paise)
)

;

CREATE INDEX ix_redemptions_user_id ON redemptions (user_id);

CREATE INDEX restaurants_coordinates_idx ON public.restaurants (latitude, longitude);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.restaurants ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.menu_items ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.searches ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.favourites ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.campaigns ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.redemptions ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ingestion_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.preferences ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.users, public.restaurants, public.menu_items, public.searches, public.favourites, public.campaigns, public.transactions, public.redemptions, public.interactions, public.ingestion_logs, public.preferences FROM anon, authenticated;
