# Bank Management System

A full-stack banking application built as a learning project, covering authentication, secure transactions, and admin controls.

## Features

User signup/login with JWT authentication
Password hashing (bcrypt)
Bank account management (create, view, close)
Deposit, withdraw, and transfer with atomic transactions
Transaction history
Daily transfer limits and minimum balance rules
Rate limiting and CAPTCHA (Google reCAPTCHA)
Admin role with account freeze/unfreeze
Automated tests (pytest)

## Tech Stack

**Backend**:Python, FastAPI, SQLAlchemy
**Database:** SQLite
**Frontend:** HTML, CSS, JavaScript
**Security:** JWT, bcrypt, reCAPTCHA, rate limiting

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r Requirement.txt`
3. Create a `.env` file with:
   .JWT_SECRET_KEY=your_secret_key
   .RECAPTCHA_SECRET_KEY=your_recaptcha_secret
   .TESTING=false

4. Run the server: `uvicorn app.main:app --reload`
5. Visit `http://127.0.0.1:8000/docs` for API documentation
6. Visit `http://127.0.0.1:8000/static/index.html` for the web interface 

## Testing

Run automated tests: `pytest test_main.py -v`

## License

MIT License