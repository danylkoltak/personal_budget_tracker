import logging
import os
from datetime import datetime, timedelta
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
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


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(create_user_request: CreateUserRequest, db: Session = Depends(get_db)):
    """
    Create a new user with a hashed password.

    Args:
        create_user_request (CreateUserRequest): The user's username and password.
        db (Session): Database session dependency.

    Returns:
        dict: Success message.
    """
    existing_user = db.query(Users).filter(Users.username == create_user_request.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")

    new_user = Users(
        username=create_user_request.username,
        hashed_password=bcrypt_context.hash(create_user_request.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency
):
    """
    Authenticate user and return an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): User credentials.
        db (Session): Database session dependency.

    Returns:
        dict: Access token and token type.
    """
    user = db.query(Users).filter(Users.username == form_data.username).first()
    if not user or not bcrypt_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    token = create_access_token(user.user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}


def create_access_token(user_id: int, expires_delta: timedelta) -> str:
    """
    Generate a JWT access token.

    Args:
        user_id (int): The user's ID.
        expires_delta (timedelta): Token expiration duration.

    Returns:
        str: Encoded JWT token.
    """
    encode = {"user_id": user_id, "exp": (datetime.now() + expires_delta).timestamp()}
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """
    Decode a JWT token and extract the user ID.

    Args:
        token (str): JWT token.

    Returns:
        int | None: User ID if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("user_id"))
    except (JWTError, ValueError):
        return None


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    access_token_cookie: str = Cookie(None)
):
    """
    Retrieve the current authenticated user.

    Args:
        request (Request): Incoming request object.
        token (str): Bearer token from the Authorization header.
        db (Session): Database session dependency.
        access_token_cookie (str, optional): Token stored in cookies.

    Returns:
        Users: Authenticated user object.

    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
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