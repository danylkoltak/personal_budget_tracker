"""Main entry point for the Personal Budget Tracker API."""

import os
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Import Modules
from src import auth
from src import pages
from src import categories
from src import expenses
from src.database import engine
from src.models import Base
from src.logging_config import logger

# Admin environment
from src.admin_app import setup_admin, create_superuser, add_session_middleware

# Load environment variables
load_dotenv()

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
routers = [auth.router, pages.router, categories.router, expenses.router]
for router in routers:
    app.include_router(router)

logger.info("FastAPI application has started")

# Template and Static Files Configuration
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

add_session_middleware(app)

setup_admin(app)

create_superuser()