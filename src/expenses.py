"""Expense management API routes for the Personal Budget Tracker."""

import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models import Category, Users, Expense
from src.database import get_db
from src.auth import get_current_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])

# Set up logger
logger = logging.getLogger(__name__)

DbDependency = Annotated[Session, Depends(get_db)]


class ExpenseCreateRequest(BaseModel):
    """Request schema for creating an expense."""
    category_id: int
    added_expense_amount: float
    expense_description: Optional[str] = None


class ExpenseResponse(BaseModel):
    """Response schema for retrieving an expense."""
    expense_id: int
    category_id: int
    added_expense_amount: float
    expense_description: Optional[str] = None
    timestamp: datetime

    class Config:
        orm_mode = True


class ExpenseUpdateRequest(BaseModel):
    """Request schema for updating an expense."""
    added_expense_amount: float
    expense_description: Optional[str] = None


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ExpenseResponse)
async def add_expense(
    expense_request: ExpenseCreateRequest,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a new expense under the specified category for the current user."""
    logger.info("User %s is adding an expense to category %s", current_user.username, expense_request.category_id)
    category = (
        db.query(Category)
        .filter(
            Category.category_id == expense_request.category_id,
            Category.user_id == current_user.user_id,
        )
        .first()
    )

    if not category:
        logger.warning("Category %s not found or unauthorized for user %s", expense_request.category_id, current_user.username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized.",
        )

    new_expense = Expense(
        category_id=expense_request.category_id,
        added_expense_amount=expense_request.added_expense_amount,
        expense_description=expense_request.expense_description,
        timestamp=datetime.now(),
    )

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    logger.info("Expense %s created successfully for category %s", new_expense.expense_id, expense_request.category_id)
    return new_expense


@router.put("/{expense_id}", status_code=status.HTTP_200_OK)
async def edit_expense(
    expense_id: int,
    expense_update: ExpenseUpdateRequest,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates an existing expense, ensuring it belongs to the authenticated user."""
    logger.info("User %s is attempting to update expense %s", current_user.username, expense_id)
    expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()

    if not expense or expense.category.user_id != current_user.user_id:
        logger.warning("Expense %s not found or unauthorized update attempt by user %s", expense_id, current_user.username)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found or unauthorized.")

    expense.added_expense_amount = expense_update.added_expense_amount
    expense.expense_description = expense_update.expense_description
    db.commit()
    db.refresh(expense)

    logger.info("Expense %s updated successfully by user %s", expense_id, current_user.username)
    return {"message": "Expense updated successfully."}

@router.get("/sum_all", response_model=dict, status_code=status.HTTP_200_OK)
async def sum_all_expenses(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates the total sum of all expenses across all categories for the current user."""
    logger.info("Calculating total expenses for user %s", current_user.username)
    total_expenses_all = (
        db.query(func.sum(Expense.added_expense_amount))
        .join(Category)
        .filter(Category.user_id == current_user.user_id)
        .scalar() or 0
    )

    logger.info("Total expenses for user %s: %.2f", current_user.username, total_expenses_all)
    return {"total_expenses_all": total_expenses_all}


@router.get("/{category_id}", response_model=List[ExpenseResponse], status_code=status.HTTP_200_OK)
async def get_expenses_for_category(
    category_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all expenses for a specific category owned by the current user."""
    logger.info("Retrieving expenses for category %s for user %s", category_id, current_user.username)
    category = (
        db.query(Category)
        .filter(Category.category_id == category_id, Category.user_id == current_user.user_id)
        .first()
    )

    if not category:
        logger.warning("Category %s not found or unauthorized for user %s", category_id, current_user.username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized.",
        )

    expenses = db.query(Expense).filter(Expense.category_id == category_id).all()

    logger.info("Retrieved %d expenses for category %s", len(expenses), category_id)
    return expenses

@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a specific expense, ensuring it belongs to the current user."""
    logger.info("User %s is attempting to delete expense %s", current_user.username, expense_id)
    expense = db.query(Expense).filter(Expense.expense_id == expense_id).first()
    if not expense or expense.category.user_id != current_user.user_id:
        logger.warning("Expense %s not found or unauthorized delete attempt by user %s", expense_id, current_user.username)
        raise HTTPException(status_code=404, detail="Expense not found or unauthorized.")

    db.delete(expense)
    db.commit()
    logger.info("Expense %s deleted successfully by user %s", expense_id, current_user.username)


@router.get("/sum/category/{category_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def sum_expenses_for_category(
    category_id: int,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculates the sum of all expenses for a specific category owned by the current user."""
    logger.info("Calculating total expenses for category %s for user %s", category_id, current_user.username)
    category = (
        db.query(Category)
        .filter(Category.category_id == category_id, Category.user_id == current_user.user_id)
        .first()
    )

    if not category:
        logger.warning("Category %s not found or unauthorized for user %s", category_id, current_user.username)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or unauthorized.",
        )
    # Sum up the expenses for this category
    total_expenses = db.query(func.sum(Expense.added_expense_amount)).filter(Expense.category_id == category_id).scalar() or 0

    logger.info("Total expenses for category %s: %.2f", category_id, total_expenses)
    return {"total_expenses": total_expenses}