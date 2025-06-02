import os
from datetime import datetime, timedelta
from typing import Annotated, Optional

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

from src.database import get_db
from src.logging_config import logger
from src.models import Users

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="templates")

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

    logger.debug("Checking if username '%s' exists", username)
    existing_user = db.query(Users).filter(Users.username == username).first()
    if existing_user:
        logger.warning("Attempted to create user but username '%s' already exists", username)
        return {"message": "A user with such username already exists"}
    
    logger.info("Creating new user with username: %s", username)
    new_user = Users(
        username=username,
        hashed_password=bcrypt_context.hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("User '%s' created successfully with ID %s", new_user.username, new_user.user_id)

    return new_user


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: DbDependency):
    logger.info("User creation request received for username: %s", create_user_request.username)
    user = create_user_in_db(create_user_request.username, create_user_request.password, db)

    if not user:
        logger.warning("User creation failed: Username '%s' already exists", create_user_request.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")
    
    return {"message": "User created successfully"}


@router.get("/register", response_class=HTMLResponse, name="register")
async def register_page(request: Request):
    """Renders the registration page."""

    logger.debug("Rendering register page")
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
        logger.warning("Registration failed: Username '%s' already exists", username)
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username already exists"
        })
    logger.info("User registered: %s (ID: %s)", user.username, user.user_id)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "message": f"Registration successful for user '{user.username}'! Please sign in with your valid credentials."
        }
    )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency
):
    logger.info("Login attempt via token endpoint - username: %s", form_data.username)
    user = db.query(Users).filter(Users.username == form_data.username).first()

    if not user or not bcrypt_context.verify(form_data.password, user.hashed_password):
        logger.warning("Invalid credentials for user: %s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    token = create_access_token(user.user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    logger.info("Access token generated for user: %s (ID: %s)", user.username, user.user_id)

    return {"access_token": token, "token_type": "bearer"}


def create_access_token(user_id: int, expires_delta: timedelta) -> str:
    logger.debug("Creating token for user ID: %s", user_id)
    encode = {"user_id": user_id, "exp": (datetime.now() + expires_delta).timestamp()}
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str | None) -> int | None:
    if not token:
        logger.warning("decode_access_token called with no token")
        return {"message": "Failed to decode access token"}
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("Token decoded successfully for user ID: %s", payload.get("user_id"))
        return int(payload.get("user_id"))
    except (JWTError, ValueError) as e:
        logger.error("Token decoding failed: %s", str(e))
        return {"message": "Failed to decode access token"}


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    logger.debug("Rendering login page")
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", name="login_post")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handles user login and sets access token."""
    logger.info("Login form submitted - username: %s", username)
    user = db.query(Users).filter(Users.username == username).first()
    if user and bcrypt_context.verify(password, user.hashed_password):

        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(user.user_id, expires_delta)
        logger.info("User logged in: %s (ID: %s)", user.username, user.user_id)
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="access_token_cookie", value=token, httponly=False, secure=False)
        return response
    
    logger.warning("Login failed for username: %s", username)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token_cookie: Optional[str] = Cookie(None)
):
    # Extract token from the Authorization header
    auth_header = request.headers.get("Authorization")
    token = None

    if auth_header:
        scheme, token_param = get_authorization_scheme_param(auth_header)
        if scheme.lower() == "bearer":
            token = token_param

    # If no token in header, try getting it from cookies
    if not token and access_token_cookie:
        token = access_token_cookie

    user_id = decode_access_token(token)
    if user_id is None:
        logger.warning("Failed to decode token or token not provided")
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
    
    logger.info("Logout request received")
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token_cookie")

    logger.info("Access token cookie deleted, user logged out")
    return response