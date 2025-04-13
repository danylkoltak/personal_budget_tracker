"""
Module for category management including creation, retrieval, and deletion.
"""

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

from models import Category, Users
from database import get_db
from auth import get_current_user

# Initialize router
router = APIRouter(prefix="/categories", tags=["Categories"])

# Set up logger
logger = logging.getLogger(__name__)

# Database dependency
DbDependency = Annotated[Session, Depends(get_db)]


class CategoryCreateRequest(BaseModel):
    """
    Schema for creating a category.
    """
    category_name: Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=100)]


class CategoryResponse(BaseModel):
    """
    Schema for category response.
    """
    category_id: int
    category_name: str

    class Config:
        orm_mode = True


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_request: CategoryCreateRequest,
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
):
    """
    Create a new category for the authenticated user.

    Args:
        category_request (CategoryCreateRequest): The category creation request data.
        current_user (Users): The currently authenticated user.
        db (Session): Database session.

    Returns:
        dict: Confirmation message with the new category ID.
    """
    existing_category = (
        db.query(Category)
        .filter(Category.category_name == category_request.category_name, Category.user_id == current_user.user_id)
        .first()
    )
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists."
        )

    new_category = Category(
        category_name=category_request.category_name,
        user_id=current_user.user_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    return {"message": f"Category '{new_category.category_name}' created successfully", "id": new_category.category_id}


@router.get("/", response_model=List[CategoryResponse], status_code=status.HTTP_200_OK)
async def see_all_categories(
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
):
    """
    Retrieve all categories belonging to the authenticated user.

    Args:
        current_user (Users): The currently authenticated user.
        db (Session): Database session.

    Returns:
        List[CategoryResponse]: A list of categories.
    """
    categories = db.query(Category).filter(Category.user_id == current_user.user_id).all()

    if not categories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No categories found."
        )

    return categories

@router.put("/{category_id}", status_code=status.HTTP_200_OK)
async def edit_category(
    category_id: int,
    category_request: CategoryCreateRequest,
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
):
    """
    Edit the name of an existing category for the authenticated user.

    Args:
        category_id (int): The ID of the category to edit.
        category_request (CategoryCreateRequest): The category update request data with the new name.
        current_user (Users): The currently authenticated user.
        db (Session): Database session.

    Returns:
        dict: Confirmation message with the updated category name.
    """
    # Check if the category exists and belongs to the authenticated user
    category = db.query(Category).filter(Category.category_id == category_id, Category.user_id == current_user.user_id).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or not authorized."
        )

    # Check if the new category name already exists for the user
    existing_category = db.query(Category).filter(Category.category_name == category_request.category_name, Category.user_id == current_user.user_id).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists."
        )

    # Update the category name
    category.category_name = category_request.category_name
    db.commit()
    db.refresh(category)

    return {"message": f"Category name updated successfully to '{category.category_name}'"}

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
    
):
    """
    Delete a category by its ID if it belongs to the authenticated user.

    Args:
        category_id (int): The ID of the category to delete.
        current_user (Users): The currently authenticated user.
        db (Session): Database session.

    Returns:
        dict: Confirmation message on successful deletion.
    """
    category = (
        db.query(Category)
        .filter(Category.category_id == category_id, Category.user_id == current_user.user_id)
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or not authorized."
        )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}