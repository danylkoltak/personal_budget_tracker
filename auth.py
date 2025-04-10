import logging
import os
from datetime import datetime, timedelta
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Users

# Load environment variables
load_dotenv()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# FastAPI router setup
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Password hashing context
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logging setup
logger = logging.getLogger(__name__)

# Template and Static Files Configuration
templates = Jinja2Templates(directory="templates")

# Database dependency
DbDependency = Annotated[Session, Depends(get_db)]


class CreateUserRequest(BaseModel):
    """Schema for user creation request."""
    username: str
    password: str


class Token(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str

def create_user_in_db(username: str, password: str, db: Session):
    """Create a user in the database after checking if the username is available."""
    existing_user = db.query(Users).filter(Users.username == username).first()
    if existing_user:
        return None
    new_user = Users(
        username=username,
        hashed_password=bcrypt_context.hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: DbDependency):
    user = create_user_in_db(create_user_request.username, create_user_request.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")
    return {"message": "User created successfully"}

@router.get("/register", response_class=HTMLResponse, name="register")
async def register_page(request: Request):
    """Renders the registration page."""
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    db: DbDependency,
    username: str = Form(...),
    password: str = Form(...),
):
    user = create_user_in_db(username, password, db)
    if not user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username already exists"
        })

    return RedirectResponse(url=request.url_for("login"), status_code=303)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency
):
    user = db.query(Users).filter(Users.username == form_data.username).first()

    if not user or not bcrypt_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    token = create_access_token(user.user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

def create_access_token(user_id: int, expires_delta: timedelta) -> str:
    encode = {"user_id": user_id, "exp": (datetime.now() + expires_delta).timestamp()}
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("user_id"))
    except (JWTError, ValueError):
        return None

@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """Renders the login page."""
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", name="login_post")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handles user login and sets access token."""
    user = db.query(Users).filter(Users.username == username).first()
    if user and bcrypt_context.verify(password, user.hashed_password):
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(user.user_id, expires_delta)
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="access_token", value=token, httponly=False, secure=False)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    access_token_cookie: str = Cookie(None)
):
  
    logger.info("Token from cookie: %s", access_token_cookie)

    # Extract token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        scheme, token_from_header = get_authorization_scheme_param(auth_header)
        if scheme.lower() == "bearer":
            token = token_from_header

    # If no token in header, try getting it from cookies
    if not token and access_token_cookie:
        token = access_token_cookie

    logger.info("Token received: %s", token)

    user_id = decode_access_token(token)
    if user_id is None:
        logger.warning("Failed token decoding or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        logger.warning("User not found for ID: %s", user_id)
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("User authenticated: %s (ID: %s)", user.username, user.user_id)
    return user

@router.get("/logout", name="logout")
async def logout():
    """Handles user logout by clearing the access token."""
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response