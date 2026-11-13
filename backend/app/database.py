import os
from datetime import datetime, timezone
from sqlalchemy import Index, create_engine, event, String, Float, Integer, Boolean, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def now():
    return datetime.now(timezone.utc).isoformat()

URL = os.getenv('DATABASE_URL', 'sqlite:///./biteai.sqlite')
from .database_tls import connection_url
database_url = connection_url(URL)
is_sqlite = database_url.get_backend_name()=='sqlite'
engine = create_engine(database_url, connect_args={'check_same_thread': False} if is_sqlite else {},
                       pool_pre_ping=True, hide_parameters=True,
                       **({} if is_sqlite else {'pool_size':3,'max_overflow':1,'pool_recycle':300}))
if is_sqlite:
    @event.listens_for(engine, 'connect')
    def sqlite_constraints(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class ProviderConnection(Base):
    __tablename__ = 'provider_connections'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    provider: Mapped[str] = mapped_column(String(30),primary_key=True)
    encrypted_tokens: Mapped[str] = mapped_column(Text)
    tool_manifest: Mapped[str] = mapped_column(Text,default='[]',server_default='[]')
    retain_until: Mapped[str] = mapped_column(String(40))
    expires_at: Mapped[str] = mapped_column(String(40))

class ProviderOAuthState(Base):
    __tablename__ = 'provider_oauth_states'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    session_id: Mapped[str] = mapped_column(String(64))
    encrypted_flow: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(String(40),index=True)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='customer')
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
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
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str] = mapped_column(Text, default='', server_default='')
    image_attribution: Mapped[str] = mapped_column(Text, default='', server_default='')
    ordering_url: Mapped[str] = mapped_column(Text, default='', server_default='')
    ownership_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    opening_hours: Mapped[str] = mapped_column(Text, default='Unknown')
    price_range: Mapped[str] = mapped_column(String(40), default='Unknown')
    source: Mapped[str] = mapped_column(Text, default='Owner supplied; unverified')
    source_id: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    sample: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)
class MenuItem(Base):
    __tablename__ = 'menu_items'
    source_key: Mapped[str | None] = mapped_column(String(96), unique=True, nullable=True)
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
    dietary: Mapped[str | None] = mapped_column(String(80),nullable=True)
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
    test_mode: Mapped[bool] = mapped_column(Boolean,default=False,server_default=text('false'))
    provider_order_id: Mapped[str | None] = mapped_column(String(100),nullable=True,index=True)
    refunded_paise: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    disputed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))
    dispute_updated_at: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
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
    search_id: Mapped[int | None] = mapped_column(ForeignKey('searches.id', ondelete='SET NULL'), nullable=True, index=True)
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

class CatalogSource(Base):
    __tablename__ = 'catalog_sources'
    __table_args__ = (Index('ux_catalog_sources_indiarestros_restaurant','restaurant_id',unique=True,postgresql_where=text("kind = 'indiarestros_api'"),sqlite_where=text("kind = 'indiarestros_api'")),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))  # osm or approved_menu
    url: Mapped[str] = mapped_column(Text)
    restaurant_id: Mapped[int | None] = mapped_column(ForeignKey('restaurants.id'), nullable=True)
    area: Mapped[str] = mapped_column(String(80))
    permission_note: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    refresh_hours: Mapped[int] = mapped_column(Integer, default=24)
    checked_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

class CatalogJob(Base):
    __tablename__ = 'catalog_jobs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('catalog_sources.id'), index=True)
    state: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[str] = mapped_column(String(40), default=now)
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    trace: Mapped[str] = mapped_column(Text, default='[]')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class MenuEvidence(Base):
    __tablename__ = 'menu_evidence'
    menu_item_id: Mapped[int] = mapped_column(ForeignKey('menu_items.id'), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('catalog_sources.id'))
    excerpt: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[str] = mapped_column(String(40))
    expires_at: Mapped[str] = mapped_column(String(40), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class SearchMatch(Base):
    __tablename__ = 'search_matches'
    id: Mapped[int] = mapped_column(primary_key=True)
    search_id: Mapped[int] = mapped_column(ForeignKey('searches.id', ondelete='CASCADE'), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey('menu_items.id'))
    price_paise: Mapped[int] = mapped_column(Integer)
    distance_km: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(Text)

class PaymentOrder(Base):
    __tablename__ = 'payment_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_order_id: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'))
    amount_paise: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20), default='created')
    test_mode: Mapped[bool] = mapped_column(Boolean,default=False,server_default=text('false'))
    created_at: Mapped[str] = mapped_column(String(40), default=now)

from sqlalchemy import Index, text
Index('catalog_one_active_job_per_source', CatalogJob.source_id, unique=True,
      sqlite_where=text("state IN ('queued', 'running')"),
      postgresql_where=text("state IN ('queued', 'running')"))


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[str] = mapped_column(String(40), index=True)


class SecurityToken(Base):
    __tablename__ = 'security_tokens'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    purpose: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[str] = mapped_column(String(40), index=True)

class RateLimit(Base):
    __tablename__ = 'rate_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[str] = mapped_column(String(40), index=True)

class OwnershipProof(Base):
    __tablename__ = 'ownership_proofs'
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    hostname: Mapped[str] = mapped_column(String(254))
    expires_at: Mapped[str] = mapped_column(String(40))
    verified_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

Index('one_attributed_click_per_match', Interaction.search_id, Interaction.restaurant_id, unique=True,
      sqlite_where=text('search_id IS NOT NULL'), postgresql_where=text('search_id IS NOT NULL'))


class PaymentAdjustment(Base):
    __tablename__ = 'payment_adjustments'
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey('transactions.id', ondelete='CASCADE'), index=True)
    reference: Mapped[str] = mapped_column(String(180), unique=True)
    kind: Mapped[str] = mapped_column(String(40))
    amount_paise: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40), default=now)

class CatalogIdentity(Base):
    """Provider aliases retain provenance without replacing existing restaurant IDs."""
    __tablename__ = 'catalog_identities'
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    licence: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(Text, default='{}')


class CampaignPolicy(Base):
    __tablename__ = 'campaign_policies'
    campaign_id: Mapped[int] = mapped_column(ForeignKey('campaigns.id',ondelete='CASCADE'),primary_key=True)
    min_tier: Mapped[str] = mapped_column(String(20),default='Bronze')
    cuisine: Mapped[str] = mapped_column(String(100),default='')
    cuisine_queries_30d: Mapped[int] = mapped_column(Integer,default=0)
    daily_budget_paise: Mapped[int] = mapped_column(Integer,default=200000)
    flat_discount_paise: Mapped[int] = mapped_column(Integer,default=0)

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    agent: Mapped[str] = mapped_column(String(30),index=True)
    status: Mapped[str] = mapped_column(String(20))
    search_id: Mapped[int | None] = mapped_column(ForeignKey('searches.id',ondelete='SET NULL'),nullable=True,index=True)
    summary: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_microrupees: Mapped[int | None] = mapped_column(Integer,nullable=True)
    created_at: Mapped[str] = mapped_column(String(40),default=now,index=True)

class ResearchRequest(Base):
    __tablename__ = 'research_requests'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    search_id: Mapped[int | None] = mapped_column(ForeignKey('searches.id',ondelete='SET NULL'),nullable=True,index=True)
    job_ids: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40),default=now,index=True)

class BronzeArtifact(Base):
    __tablename__ = 'bronze_artifacts'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('catalog_sources.id'),index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(40),default=now,index=True)


class DealVoucher(Base):
    __tablename__ = 'deal_vouchers'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    payment_order_id: Mapped[int] = mapped_column(ForeignKey('payment_orders.id'),unique=True)
    redemption_id: Mapped[int] = mapped_column(ForeignKey('redemptions.id'),unique=True)
    state: Mapped[str] = mapped_column(String(20),default='pending')
    expires_at: Mapped[str] = mapped_column(String(40),index=True)
    redeemed_at: Mapped[str | None] = mapped_column(String(40),nullable=True)

class RestaurantClaim(Base):
    __tablename__ = 'restaurant_claims'
    id: Mapped[str] = mapped_column(String(64),primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey('restaurants.id'),index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'),index=True)
    business_reference: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(20),default='pending')
    review_note: Mapped[str] = mapped_column(Text,default='')
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'),nullable=True)
    created_at: Mapped[str] = mapped_column(String(40),default=now)

Index('ix_menu_items_available_coverage',MenuItem.id,postgresql_include=['restaurant_id'],postgresql_where=MenuItem.available.is_(True)).ddl_if(dialect='postgresql')
Index('ix_menu_evidence_active_coverage',MenuEvidence.menu_item_id,postgresql_include=['expires_at'],postgresql_where=MenuEvidence.active.is_(True)).ddl_if(dialect='postgresql')
Index('ix_catalog_identities_observed_at',CatalogIdentity.observed_at).ddl_if(dialect='postgresql')
