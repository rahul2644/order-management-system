from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app import schemas
from app.deps import DB, AdminUser, CurrentUser
from app.models import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(db: DB, _: CurrentUser):
    return db.scalars(select(Category).order_by(Category.name)).all()


@router.post("", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: schemas.CategoryCreate, db: DB, _: CurrentUser):
    if db.scalar(select(Category).where(Category.name.ilike(payload.name))):
        raise HTTPException(status.HTTP_409_CONFLICT, "Category already exists")
    category = Category(name=payload.name.strip())
    db.add(category)
    db.commit()
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DB, _: AdminUser):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    db.delete(category)
    db.commit()
