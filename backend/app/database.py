import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, String, Float, Integer, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now():
    return datetime.now(timezone.utc).isoformat()

URL = os.getenv('DATABASE_URL', 'sqlite:///./biteai.sqlite')
# Render uses postgres://; SQLAlchemy's psycopg driver requires its explicit dialect.
if URL.startswith('postgres://'):
    URL = URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif URL.startswith('postgresql://'):
    URL = URL.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(URL, connect_args={'check_same_thread': False} if URL.startswith('sqlite') else {})
if URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_constraints(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='customer')
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
class Restaurant(Base):
    __tablename__ = 'restaurants'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(Text)
    area: Mapped[str] = mapped_column(String(80), index=True)
    pin_code: Mapped[str] = mapped_column(String(6), default='')
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    cuisine: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str] = mapped_column(String(30), default='')
    website: Mapped[str] = mapped_column(Text, default='')
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_hours: Mapped[str] = mapped_column(Text, default='Unknown')
    price_range: Mapped[str] = mapped_column(String(40), default='Unknown')
    source: Mapped[str] = mapped_column(Text, default='Owner supplied; unverified')
    source_id: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    sample: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
class MenuItem(Base):
    __tablename__ = 'menu_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    category: Mapped[str] = mapped_column(String(80), default='Main')
    cuisine: Mapped[str] = mapped_column(String(100))
    price_paise: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default='')
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(Text, default='Owner supplied; unverified')
    verified_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
class Search(Base):
    __tablename__ = 'searches'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text)
    cuisine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dish: Mapped[str | None] = mapped_column(String(150), nullable=True)
    budget: Mapped[int] = mapped_column(Integer)
    area: Mapped[str] = mapped_column(String(80))
    results: Mapped[int] = mapped_column(Integer)
    trace: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
class Favourite(Base):
    __tablename__ = 'favourites'
    __table_args__ = (UniqueConstraint('user_id','restaurant_id','menu_item_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'))
    menu_item_id: Mapped[int] = mapped_column(Integer, default=0)
class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), index=True)
    title: Mapped[str] = mapped_column(String(100))
    percent: Mapped[int] = mapped_column(Integer)
    min_searches: Mapped[int] = mapped_column(Integer, default=0)
    min_spend_paise: Mapped[int] = mapped_column(Integer, default=0)
    min_visits: Mapped[int] = mapped_column(Integer, default=0)
    min_order_paise: Mapped[int] = mapped_column(Integer, default=0)
    max_discount_paise: Mapped[int] = mapped_column(Integer)
    redemption_limit: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[str] = mapped_column(String(40), default=now)
    ends_at: Mapped[str] = mapped_column(String(40))
class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'))
    reference: Mapped[str] = mapped_column(String(100), unique=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
class Redemption(Base):
    __tablename__ = 'redemptions'
    __table_args__ = (UniqueConstraint('user_id','campaign_id','sequence'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey('campaigns.id'))
    sequence: Mapped[int] = mapped_column(Integer)
    order_paise: Mapped[int] = mapped_column(Integer)
    discount_paise: Mapped[int] = mapped_column(Integer)
    audit: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
class Interaction(Base):
    __tablename__ = 'interactions'
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class IngestionLog(Base):
    __tablename__ = 'ingestion_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), index=True)
    source: Mapped[str] = mapped_column(Text)
    trace: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

from sqlalchemy import CheckConstraint
for table, expression, name in [
    (MenuItem.__table__, 'price_paise > 0', 'positive_menu_price'),
    (Transaction.__table__, 'amount_paise > 0', 'positive_transaction'),
    (Campaign.__table__, 'percent BETWEEN 1 AND 80 AND max_discount_paise > 0 AND redemption_limit > 0', 'valid_campaign'),
    (Redemption.__table__, 'discount_paise >= 0 AND discount_paise <= order_paise', 'valid_redemption'),
    (Restaurant.__table__, 'latitude BETWEEN 18.85 AND 19.35 AND longitude BETWEEN 72.75 AND 73.05', 'mumbai_coordinates'),
]:
    table.append_constraint(CheckConstraint(expression, name=name))

class Preference(Base):
    __tablename__ = 'preferences'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    preferred_cuisine: Mapped[str] = mapped_column(String(100), default='')
