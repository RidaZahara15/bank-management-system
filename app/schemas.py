from pydantic import BaseModel, EmailStr
from datetime import datetime


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



class DepositRequest(BaseModel):
    amount: float


class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: float
    timestamp: datetime
    account_id: int

    class Config:
        from_attributes = True


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float