# Import all schemas to make them available through the package

# User schemas
from core.schemas.user import User, UserCreate, UserUpdate, UserInDB, UserLogin

# Auth schemas
from core.schemas.token import Token, TokenData

# Chat schemas
from core.schemas.message import Message, MessageCreate, MessageResponse
from core.schemas.ai_partner import AIPartner, AIPartnerCreate, AIPartnerUpdate

# Gift schemas - Make sure these are included
from core.schemas.gift import GiftRequest, GiftResponse

# API response schemas
from core.schemas.response import SuccessResponse, ErrorResponse
