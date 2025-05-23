"""This module defines database models for Users, Categories, and Expenses."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.orm import relationship
from src.database import Base


class Users(Base):
    """Represents a user in the system."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.user_id}, username='{self.username}')>"


class Category(Base):
    """Represents a spending category associated with a user."""

    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    expenses = relationship("Expense", back_populates="category", cascade="all, delete-orphan")
    user = relationship("Users", back_populates="categories")

    __table_args__ = (
        UniqueConstraint('category_name', 'user_id', name='uq_category_user'),
    )

    def __repr__(self):
        return f"<Category(id={self.category_id}, name='{self.category_name}', user_id={self.user_id})>"


class Expense(Base):
    """Represents an expense under a specific category."""
    
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True)
    category_id = Column(
        Integer, ForeignKey("categories.category_id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_expense_amount = Column(Float, nullable=False)
    expense_description = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    category = relationship("Category", back_populates="expenses")

    __table_args__ = (
        CheckConstraint("added_expense_amount > 0", name="check_positive_expense_amount"),
    )

    def __repr__(self):
        return (
            f"<Expense(id={self.expense_id}, category_id={self.category_id}, "
            f"amount={self.added_expense_amount}, description='{self.expense_description}', "
            f"timestamp={self.timestamp})>"
        )