from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SubscriptionType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class StarsPackageType(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    PREMIUM = "premium"


class Subscription(BaseModel):
    id: str
    name: str
    description: str
    type: SubscriptionType
    price: float
    currency: str = "USD"
    duration_days: int
    features: List[str]
    is_popular: bool = False
    
    class Config:
        from_attributes = True


class StarsPackage(BaseModel):
    id: str
    name: str
    description: str
    type: StarsPackageType
    price: float
    currency: str = "USD"
    stars_amount: int
    bonus_stars: int = 0
    is_popular: bool = False
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    subscriptions: List[Subscription]
    total: int
    
    class Config:
        from_attributes = True


class StarsPackageResponse(BaseModel):
    packages: List[StarsPackage]
    total: int
    
    class Config:
        from_attributes = True


class SubscriptionPurchase(BaseModel):
    subscription_id: str
    payment_method: str
    

class StarsPackagePurchase(BaseModel):
    package_id: str
    payment_method: str


class PurchaseResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    purchase_date: Optional[datetime] = None