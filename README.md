# Bank Management System

A full-stack banking application built as a learning project — covering authentication, secure transactions, admin controls, and automated testing.

## Features

- User signup/login with JWT authentication
- Password hashing (bcrypt)
- Bank account management (create, view, close)
- Deposit, withdraw, and transfer with atomic transactions
- Daily transfer limits and minimum balance rules
- Transaction history
- Rate limiting (per-IP and per-email) and CAPTCHA (Google reCAPTCHA)
- Admin role with account freeze/unfreeze
- Automated tests (pytest)
- Multi-page frontend (login, dashboard, transactions, admin panel)

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Security:** JWT, bcrypt, reCAPTCHA, rate limiting, environment variables

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r Requirement.txt`
3. Create a `.env` file with:
   .JWT_SECRET_KEY=your_secret_key
   .RECAPTCHA_SECRET_KEY=your_recaptcha_secret
   .TESTING=false

4. Run the server: `uvicorn app.main:app --reload`
5. Visit `http://127.0.0.1:8000/static/index.html` to use the app
6. Visit `http://127.0.0.1:8000/docs` for API documentation

## Testing

Run automated tests: `pytest test_main.py -v`

## Project Structure

├── app/
│ ├── main.py - API endpoints
│ ├── database.py - Database connection
│ ├── models.py - Database tables
│ ├── schemas.py - Request/response validation
│ └── auth.py - Authentication logic
├── static/
│ ├── index.html - Login/Signup page
│ ├── dashboard.html - User dashboard
│ ├── transactions.html - Transaction history
│ └── admin.html - Admin panel
├── test_main.py - Automated tests
└── Requirement.txt - Dependencies


## License

MIT License




