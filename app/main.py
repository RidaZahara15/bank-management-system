from fastapi import FastAPI
from app.database import engine, Base
from app import models
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import schemas 
from fastapi import Depends
from app import auth
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import random
import string
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import httpx
from dotenv import load_dotenv
import os
from fastapi.responses import HTMLResponse

load_dotenv()
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bank Management API")
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


# Rate limiter setup - tracks requests per IP address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


RECAPTCHA_SECRET_KEY =os.getenv("Recaptcha_Secret_key")


security = HTTPBearer()


# Gives each request its own database session, closes it when done
def get_db():
    db = SessionLocal()   
    try:
        yield db         #give this session to endpoint for use
    finally:
        db.close()


# Checks reCAPTCHA response with Google's servers
async def verify_captcha(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={"secret": RECAPTCHA_SECRET_KEY, "response": token}
    )
    result = response.json()
    return result.get("success", False)


# Reads the token from the request, checks it, and returns the logged-in user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = auth.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == payload.get("user_id")).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user



# Blocks the request unless the logged-in user is an admin
def require_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def generate_account_number():
    return "ACC" + "".join(random.choices(string.digits, k=8))


@app.get("/")
def read_root():
    return {"message": "Bank API is running", "status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Signs up a new user, hashes their password before saving
@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=auth.hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# Returns the logged-in user's own profile
@app.get("/profile", response_model=schemas.UserResponse)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user



# Logs a user in - checks credentials, CAPTCHA, and rate limits by email too
@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    if os.getenv("TESTING") == "true":
        is_human = True
    else:
        is_human = await verify_captcha(credentials.captcha_token)


    if not is_human:
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed")
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)


    # Block this email if it's had too many failed attempts in the last minute
    recent_attempts = db.query(models.LoginAttempt).filter(
        models.LoginAttempt.email == credentials.email,
        models.LoginAttempt.timestamp >= one_minute_ago
    ).count()

    if recent_attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts for this email. Try again later.")

    user = db.query(models.User).filter(models.User.email == credentials.email).first()


    # Same error message for both cases so attackers can't tell which one was wrong
    if not user or not auth.verify_password(credentials.password, user.password_hash):
        failed_attempt = models.LoginAttempt(email=credentials.email)
        db.add(failed_attempt)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth.create_access_token(data={"user_id": user.id, "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


# Opens a new bank account for the logged-in user
@app.post("/accounts", response_model=schemas.AccountResponse)
def create_account(
    account: schemas.AccountCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_account = models.Account(
        account_number=generate_account_number(),
        account_type=account.account_type,
        balance=0.0,
        user_id=current_user.id
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account



# Lists only the accounts that belong to the logged-in user
@app.get("/accounts", response_model=list[schemas.AccountResponse])
def get_my_accounts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    return accounts



# Gets one specific account - only if it belongs to the logged-in user
@app.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def get_account(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this account")

    return account


# Closes an account - withdraws any remaining balance first, then deletes it
@app.delete("/accounts/{account_id}")
def close_account(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to close this account")

    if account.balance > 0:
        final_withdrawal = models.Transaction(
            type="withdraw",
            amount=account.balance,
            account_id=account.id
        )
    db.add(final_withdrawal)
    account.balance = 0
    db.delete(account)
    db.commit()
    return {"message": "Account closed successfully and remaining balance was withdrawn"}



# Deposits money into an account and logs it as a transaction
@app.post("/accounts/{account_id}/deposit", response_model=schemas.TransactionResponse)
def deposit(
    account_id: int,
    deposit_data: schemas.DepositRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if account.is_frozen:
        raise HTTPException(status_code=403, detail="This account is frozen")

    if deposit_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be positive")

    account.balance += deposit_data.amount

    new_transaction = models.Transaction(
        type="deposit",
        amount=deposit_data.amount,
        account_id=account.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction



# Withdraws money - blocks it if it would break the minimum balance rule
@app.post("/accounts/{account_id}/withdraw", response_model=schemas.TransactionResponse)
def withdraw(
    account_id: int,
    withdraw_data: schemas.DepositRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    
    if account.is_frozen:
        raise HTTPException(status_code=403, detail="This account is frozen")

    if withdraw_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be positive")

    if withdraw_data.amount > account.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    

    MINIMUM_BALANCE = 100

    if account.balance - withdraw_data.amount < MINIMUM_BALANCE:
        raise HTTPException(status_code=400, detail=f"Cannot withdraw - minimum balance of {MINIMUM_BALANCE} must be maintained")

    account.balance -= withdraw_data.amount

    new_transaction = models.Transaction(
        type="withdraw",
        amount=withdraw_data.amount,
        account_id=account.id
    )
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    return new_transaction


# Transaction history for one specific account, newest first
@app.get("/accounts/{account_id}/transactions", response_model=list[schemas.TransactionResponse])
def get_transaction_history(
    account_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    

    transactions = db.query(models.Transaction).filter(
        models.Transaction.account_id == account_id
    ).order_by(models.Transaction.timestamp.desc()).all()

    return transactions



# Adds up the balance across all of the user's accounts
@app.get("/accounts/summary/total-balance")
def get_total_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    total = sum(account.balance for account in accounts)
    return {"total_balance": total, "number_of_accounts": len(accounts)}


# Moves money between two accounts - both sides succeed together or not at all
@app.post("/transfer")
def transfer(
    transfer_data: schemas.TransferRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if transfer_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    if transfer_data.from_account_id == transfer_data.to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    from_account = db.query(models.Account).filter(models.Account.id == transfer_data.from_account_id).first()
    to_account = db.query(models.Account).filter(models.Account.id == transfer_data.to_account_id).first()

    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    if from_account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to transfer from this account")

    if transfer_data.amount > from_account.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    
    if from_account.is_frozen:   # <- SIRF ye check hota hai
        raise HTTPException(status_code=403, detail="Your account is frozen")


    MINIMUM_BALANCE = 100
    DAILY_TRANSFER_LIMIT = 50000
    if from_account.balance - transfer_data.amount < MINIMUM_BALANCE:
        raise HTTPException(status_code=400, detail=f"Cannot transfer - minimum balance of {MINIMUM_BALANCE} must be maintained")    
    


    
# Check how much this account has already sent out today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    today_transfers = db.query(models.Transaction).filter(
        models.Transaction.account_id == from_account.id,
        models.Transaction.type == "transfer_out",
        models.Transaction.timestamp >= today_start
    ).all()

    total_today = sum(t.amount for t in today_transfers)

    if total_today + transfer_data.amount > DAILY_TRANSFER_LIMIT:
        raise HTTPException(status_code=400, detail=f"Daily transfer limit of {DAILY_TRANSFER_LIMIT} exceeded")

# Both balance changes and both transaction records happen together, or roll back
    try:
        from_account.balance -= transfer_data.amount
        to_account.balance += transfer_data.amount

        debit_transaction = models.Transaction(
            type="transfer_out",
            amount=transfer_data.amount,
            account_id=from_account.id
        )
        credit_transaction = models.Transaction(
            type="transfer_in",
            amount=transfer_data.amount,
            account_id=to_account.id
        )

        db.add(debit_transaction)
        db.add(credit_transaction)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer failed, no changes were made")

    return {
        "message": "Transfer successful",
        "from_account": from_account.account_number,
        "to_account": to_account.account_number,
        "amount": transfer_data.amount
    }


# Combined history across ALL of the user's accounts, newest first
@app.get("/transactions", response_model=list[schemas.TransactionResponse])
def get_all_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    account_ids = [account.id for account in user_accounts]

    transactions = db.query(models.Transaction).filter(
        models.Transaction.account_id.in_(account_ids)
    ).order_by(models.Transaction.timestamp.desc()).all()

    return transactions



#For testing XSS Script

@app.get("/demo-vulnerable")
def demo_vulnerable(name: str):
    return HTMLResponse(f"<h1>Welcome, {name}!</h1>")


@app.get("/demo-safe")
def demo_safe(name: str):
    return {"message": f"Welcome, {name}!"}



# Admin-only: lists every account in the system, not just one user's
@app.get("/admin/accounts", response_model=list[schemas.AccountResponse])
def get_all_accounts(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    accounts = db.query(models.Account).all()
    return accounts


# Admin-only: freezes an account so deposits/withdrawals/transfers get blocked
@app.post("/admin/accounts/{account_id}/freeze")
def freeze_account(account_id: int, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_frozen = True
    db.commit()
    return {"message": "Account frozen successfully"}




# Admin-only: unfreezes an account, letting normal activity resume
@app.post("/admin/accounts/{account_id}/unfreeze")
def unfreeze_account(account_id: int, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_frozen = False
    db.commit()
    return {"message": "Account unfrozen successfully"}