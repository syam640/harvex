from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Expense, CropCycle, Field, Farm
from app.schemas.schemas import ExpenseCreate, ExpenseResponse

router = APIRouter(prefix="/api/crop-cycles", tags=["expenses"])

VALID_EXPENSE_CATEGORIES = {"Seeds", "Fertilizer", "Pesticides", "Labour", "Irrigation", "Transport", "Equipment", "Other"}

def _verify_cycle_ownership(cycle_id: int, user: User, db: Session) -> CropCycle:
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == cycle_id,
        Farm.user_id == user.id
    ).first()
    if not crop_cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found"
        )
    return crop_cycle

def _verify_expense_ownership(expense_id: int, user: User, db: Session) -> Expense:
    expense = db.query(Expense).join(CropCycle).join(Field).join(Farm).filter(
        Expense.id == expense_id,
        Farm.user_id == user.id
    ).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    return expense

@router.get("/{cycle_id}/expenses", response_model=List[ExpenseResponse])
def get_expenses(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    expenses = db.query(Expense).filter(Expense.crop_cycle_id == cycle_id).all()
    return [ExpenseResponse.model_validate(expense) for expense in expenses]

@router.post("/{cycle_id}/expenses", response_model=ExpenseResponse)
def create_expense(
    cycle_id: int,
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)

    if expense_data.category not in VALID_EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {expense_data.category}. Valid: {sorted(VALID_EXPENSE_CATEGORIES)}"
        )
    if expense_data.amount <= 0 or expense_data.amount > 1000000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be between ₹1 and ₹10,00,000"
        )
    if expense_data.description and len(expense_data.description) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description must be 500 characters or fewer"
        )

    expense = Expense(
        crop_cycle_id=cycle_id,
        category=expense_data.category,
        amount=expense_data.amount,
        description=expense_data.description,
        expense_date=expense_data.expense_date
    )
    db.add(expense)
    try:
        db.commit()
        db.refresh(expense)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create expense.")

    return ExpenseResponse.model_validate(expense)

@router.put("/{cycle_id}/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    cycle_id: int,
    expense_id: int,
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    expense = _verify_expense_ownership(expense_id, current_user, db)

    if expense.crop_cycle_id != cycle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense does not belong to this crop cycle"
        )
    if expense_data.category not in VALID_EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {expense_data.category}. Valid: {sorted(VALID_EXPENSE_CATEGORIES)}"
        )
    if expense_data.amount <= 0 or expense_data.amount > 1000000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be between ₹1 and ₹10,00,000"
        )

    expense.category = expense_data.category
    expense.amount = expense_data.amount
    expense.description = expense_data.description
    expense.expense_date = expense_data.expense_date
    try:
        db.commit()
        db.refresh(expense)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update expense.")

    return ExpenseResponse.model_validate(expense)

@router.delete("/{cycle_id}/expenses/{expense_id}")
def delete_expense(
    cycle_id: int,
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    expense = _verify_expense_ownership(expense_id, current_user, db)

    if expense.crop_cycle_id != cycle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense does not belong to this crop cycle"
        )

    db.delete(expense)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to delete expense.")

    return {"message": "Expense deleted successfully", "deleted_id": expense_id}
