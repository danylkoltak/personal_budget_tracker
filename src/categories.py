"""
Module for category management including creation, retrieval, and deletion.
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

from src.logging_config import logger
from src.models import Category, Users
from src.database import get_db
from src.auth import get_current_user

# Initialize router
router = APIRouter(prefix="/categories", tags=["Categories"])

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
    logger.info(f"Attempting to create category '{category_request.category_name}' for user {current_user.username}")
    existing_category = (
        db.query(Category)
        .filter(Category.category_name == category_request.category_name, Category.user_id == current_user.user_id)
        .first()
    )
    if existing_category:
        logger.warning(f"Category creation failed: '{category_request.category_name}' already exists for user {current_user.username}")
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
    logger.info(f"Category '{new_category.category_name}' created successfully for user {current_user.username}")
    return {"message": f"Category '{new_category.category_name}' created successfully", "id": new_category.category_id}


@router.get("/", response_model=List[CategoryResponse], status_code=status.HTTP_200_OK)
async def see_all_categories(
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
):
    logger.info(f"Retrieving all categories for user {current_user.username}")
    categories = db.query(Category).filter(Category.user_id == current_user.user_id).all()

    if not categories:
        logger.warning(f"No categories found for user {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No categories found."
        )
    logger.info(f"Found {len(categories)} categories for user {current_user.username}")
    return categories

@router.put("/{category_id}", response_model=CategoryResponse, status_code=status.HTTP_200_OK)
async def edit_category(
    category_id: int,
    category_request: CategoryCreateRequest,
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
):
    logger.info(f"User {current_user.username} attempting to update category ID {category_id} to '{category_request.category_name}'")
    # Check if the category exists and belongs to the authenticated user
    category = db.query(Category).filter(Category.category_id == category_id, Category.user_id == current_user.user_id).first()

    if not category:
        logger.error(f"Category ID {category_id} not found or unauthorized for user {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or not authorized."
        )

    # Check if the new category name already exists for the user
    existing_category = db.query(Category).filter(Category.category_name == category_request.category_name, Category.user_id == current_user.user_id).first()
    if existing_category:
        logger.warning(f"Category name '{category_request.category_name}' already exists for user {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists."
        )

    # Update the category name
    category.category_name = category_request.category_name
    db.commit()
    db.refresh(category)
    logger.info(f"Category ID {category_id} updated to '{category.category_name}' by user {current_user.username}")
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: DbDependency,
    current_user: Users = Depends(get_current_user),
    
):
    logger.info(f"User {current_user.username} attempting to delete category ID {category_id}")
    category = (
        db.query(Category)
        .filter(Category.category_id == category_id, Category.user_id == current_user.user_id)
        .first()
    )
    if not category:
        logger.error(f"Delete failed: Category ID {category_id} not found or unauthorized for user {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or not authorized."
        )

    db.delete(category)
    db.commit()
    logger.info(f"Category ID {category_id} deleted successfully by user {current_user.username}")
    return {"message": "Category deleted successfully"}