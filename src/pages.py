from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from src.database import get_db
from src.models import Users, Category, Expense
from src.auth import get_current_user

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Main pages"])


@router.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request):
    """Renders the home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db), current_user: Users = Depends(get_current_user)):
    """Renders the user dashboard if authenticated."""
    user_categories = (
        db.query(Category)
        .filter(Category.user_id == current_user.user_id)
        .options(joinedload(Category.expenses))
        .all()
    )

    for category in user_categories:
        category.total_expenses = sum(expense.added_expense_amount for expense in category.expenses)

    total_expenses_all = (
        db.query(func.sum(Expense.added_expense_amount))
        .join(Category)
        .filter(Category.user_id == current_user.user_id)
        .scalar()
    ) or 0.0

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "categories": user_categories,
            "total_expenses_all": total_expenses_all,
        },
    )