"""Main entry point for the Personal Budget Tracker API."""

import logging
import os
from datetime import timedelta
from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from dotenv import load_dotenv

# Import Modules
import auth
import categories
import expenses
from database import get_db, engine
from models import Base, Users, Category, Expense
from auth import create_access_token, bcrypt_context, ACCESS_TOKEN_EXPIRE_MINUTES, decode_access_token

# Load environment variables
load_dotenv()


def setup_logging():
    """Configures logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("app.log"),  # Log to a file
            logging.StreamHandler()  # Log to console
        ],
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# Database Setup
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully")

# FastAPI App Instance with Metadata
app = FastAPI(
    title="Personal Budget Tracker API",
    description="Manage categories, expenses, and authentication securely.",
    version="1.0",
    contact={"name": "Your Name", "email": "your.email@example.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# Secret Key for Session Middleware
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret")

# Include Routers Dynamically
routers = [auth.router, categories.router, expenses.router]
for router in routers:
    app.include_router(router)

logger.info("FastAPI application has started")

# Template and Static Files Configuration
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renders the home page."""
    return templates.TemplateResponse("base.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Renders the user dashboard if authenticated."""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)

    try:
        user_id = decode_access_token(token)
    except Exception:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Fetch user categories along with their expenses in one query
    user_categories = (
        db.query(Category)
        .filter(Category.user_id == user.user_id)
        .options(joinedload(Category.expenses))
        .all()
    )

    # Calculate total expenses per category in Python
    for category in user_categories:
        category.total_expenses = sum(expense.added_expense_amount for expense in category.expenses)

    #Fetch total expenses across all categories for the user
    total_expenses_all = (
        db.query(func.sum(Expense.added_expense_amount))
        .join(Category)
        .filter(Category.user_id == user.user_id)
        .scalar()
    ) or 0.0  # Ensures it returns a number, not None   

    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user, "categories": user_categories, "total_expenses_all": total_expenses_all},
    )