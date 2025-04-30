import os
import jwt
from dotenv import load_dotenv
from fastapi import Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from wtforms.fields import PasswordField
from wtforms.validators import Optional

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from src.database import SessionLocal
from passlib.context import CryptContext

from sqladmin import Admin, ModelView

from src.auth import get_current_user
from src.database import engine
from src.models import Users, Category, Expense

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

templates = Jinja2Templates(directory="templates")

def add_session_middleware(app):
    secret_key = os.getenv("SECRET_KEY", "change_this_secret")
    app.add_middleware(SessionMiddleware, secret_key=secret_key)

def create_superuser():
    db: Session = SessionLocal()
    try:
        username = os.getenv("SUPERUSER_USERNAME")
        password = os.getenv("SUPERUSER_PASSWORD")

        if not username or not password:
            print("Superuser credentials are missing in .env")
            return

        existing_user = db.query(Users).filter(Users.username == username).first()
        if existing_user:
            print(f"Superuser '{username}' already exists.")
            return

        hashed_password = pwd_context.hash(password)
        superuser = Users(
            username=username,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True
        )
        db.add(superuser)
        db.commit()
        print(f"Superuser '{username}' created successfully.")
    except Exception as e:
        print(f"Error creating superuser: {e}")
    finally:
        db.close()

class AdminAuth(AuthenticationBackend):
    def __init__(self):
        super().__init__(secret_key=SECRET_KEY)

    async def authenticate(self, request: Request):
        token = request.session.get("token")
        if not token:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                return None

            db = SessionLocal()
            user = db.query(Users).filter(Users.user_id == user_id).first()
            db.close()

            if user and user.is_superuser:
                return user
        except jwt.PyJWTError:
            return None

    async def login(self, request: Request):
        if request.method == "GET":
            return templates.TemplateResponse("admin_login.html", {"request": request})

        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        db = SessionLocal()
        user = db.query(Users).filter(Users.username == username).first()
        db.close()

        if user and user.is_superuser and pwd_context.verify(password, user.hashed_password):
            token = jwt.encode({"user_id": user.user_id}, SECRET_KEY, algorithm="HS256")
            request.session["token"] = token
            return RedirectResponse(url="/admin", status_code=302)

        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "Invalid credentials"
        })

    async def logout(self, request: Request):
        request.session.clear()
        return RedirectResponse(url="/")

# Define views for your models
class UsersAdmin(ModelView, model=Users):
    column_list = [Users.user_id, Users.username, Users.hashed_password, Users.is_superuser]

    form_excluded_columns = ["categories"]

    form_extra_fields = {
        "password": PasswordField("Password", validators=[Optional()])
    }
    async def on_model_change(self, request: Request, model: Users, form_data: dict, is_created: bool):
        password = form_data.get("password")
        if password:
            model.hashed_password = pwd_context.hash(password)

class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.category_id, Category.category_name, Category.user_id]

class ExpenseAdmin(ModelView, model=Expense):
    column_list = [Expense.expense_id, Expense.added_expense_amount, Expense.timestamp, Expense.expense_description, Expense.category_id]

def setup_admin(app):
    from admin_app import AdminAuth
    admin = Admin(app=app, engine=engine, authentication_backend=AdminAuth())

    admin.add_view(UsersAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(ExpenseAdmin)