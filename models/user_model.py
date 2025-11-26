# models/user_model.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional

class WishlistItem(BaseModel):
    productId: str
    name: str
    image: str
    price: float

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: Optional[str] = Field(default=None, alias="_id")
    wishlist: List[WishlistItem] = Field(default_factory=list)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
