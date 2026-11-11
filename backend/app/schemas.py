from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal
class Register(BaseModel):
    email: str = Field(max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    name: str = Field(min_length=1,max_length=80)
    password: str = Field(min_length=10,max_length=128)
    role: Literal['customer','owner'] = 'customer'
    @field_validator('name')
    @classmethod
    def nonblank_name(cls,value):
        if not value.strip(): raise ValueError('Name cannot be blank')
        return value.strip()
class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
class SearchInput(BaseModel):
    query: str = Field(default='',max_length=500)
    area: str = 'Bandra'
    latitude: float | None = Field(default=None,ge=18.85,le=19.35)
    longitude: float | None = Field(default=None,ge=72.75,le=73.05)
    budget: int = Field(default=500,ge=1,le=100000)
    radius_km: float = Field(default=5,gt=0,le=50)
    include_samples: bool = True
class RestaurantInput(BaseModel):
    name: str = Field(min_length=2,max_length=150)
    address: str = Field(min_length=5,max_length=500)
    area: Literal['Bandra','Andheri','Powai','Colaba','Dadar']
    latitude: float = Field(ge=18.85,le=19.35)
    longitude: float = Field(ge=72.75,le=73.05)
    cuisine: str = Field(min_length=2,max_length=100)
    pin_code: str = Field(default='',pattern=r'^(\d{6})?$')
    phone: str = Field(default='',max_length=30)
    website: str = Field(default='',max_length=500)
    opening_hours: str = Field(default='Unknown',max_length=500)
    @field_validator('website')
    @classmethod
    def safe_url(cls,value):
        if value and not value.startswith('https://'): raise ValueError('Use an HTTPS website')
        return value
class MenuInput(BaseModel):
    name: str = Field(min_length=2,max_length=150)
    cuisine: str = Field(min_length=2,max_length=100)
    category: str = Field(default='Main',max_length=80)
    price_paise: int = Field(ge=1,le=10000000)
    description: str = Field(default='',max_length=1000)
    available: bool = True
class CampaignInput(BaseModel):
    title: str = Field(min_length=2,max_length=100)
    percent: int = Field(ge=1,le=80)
    min_searches: int = Field(default=0,ge=0,le=10000)
    min_spend_paise: int = Field(default=0,ge=0,le=100000000)
    min_visits: int = Field(default=0,ge=0,le=10000)
    min_order_paise: int = Field(default=0,ge=0,le=10000000)
    max_discount_paise: int = Field(ge=1,le=10000000)
    redemption_limit: int = Field(default=1,ge=1,le=100)
    starts_at: datetime
    ends_at: datetime
class TransactionInput(BaseModel):
    restaurant_id: int
    amount_paise: int = Field(ge=1,le=10000000)
class RedeemInput(BaseModel):
    order_paise: int = Field(ge=1,le=10000000)
class ConsentInput(BaseModel):
    consent: bool
class IngestionInput(BaseModel):
    source: str = Field(min_length=5,max_length=500)
    items: list[MenuInput] = Field(min_length=1,max_length=100)
    permission_confirmed: bool

class ProfileInput(BaseModel):
    name: str = Field(min_length=1,max_length=80)
    preferred_cuisine: Literal['','Chinese','Indian','Italian','Japanese','Mexican','South Indian'] = ''

class MenuSourceInput(BaseModel):
    url: str = Field(max_length=1000)
    permission_note: str = Field(min_length=10,max_length=500)
    refresh_hours: int = Field(default=24,ge=6,le=168)

class SourceState(BaseModel):
    enabled: bool
