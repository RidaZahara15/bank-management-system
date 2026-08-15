from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


        
class UserLogin(BaseModel):
    email: EmailStr
    password: str



class AccountCreate(BaseModel):
    account_type: str = "savings"


class AccountResponse(BaseModel):
    id: int
    account_number: str
    balance: float
    account_type: str

    class Config:
        from_attributes = True