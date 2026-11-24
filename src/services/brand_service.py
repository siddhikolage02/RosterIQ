
from sqlalchemy.orm import Session

from src.database.models import Brand


def create_brand(
    db: Session,
    name: str,
    description: str = None,
):
    """Create a new brand."""

    name = name.strip()

    if not name:
        raise ValueError("Brand name is required.")

    # Check whether the brand already exists
    existing_brand = (
        db.query(Brand)
        .filter(Brand.name == name)
        .first()
    )

    if existing_brand:
        raise ValueError("This brand already exists.")

    brand = Brand(
        name=name,
        description=description.strip() if description else None,
        is_active=True,
    )

    try:
        db.add(brand)
        db.commit()
        db.refresh(brand)
        return brand

    except Exception:
        db.rollback()
        raise


def get_brand_by_id(db: Session, brand_id: int):
    """Retrieve a brand using its ID."""

    return (
        db.query(Brand)
        .filter(Brand.id == brand_id)
        .first()
    )


def get_all_brands(db: Session):
    """Retrieve all brands."""

    return (
        db.query(Brand)
        .order_by(Brand.id)
        .all()
    )


def update_brand(db: Session, brand_id: int, **updates):
    """Update brand information."""

    brand = get_brand_by_id(db, brand_id)

    if not brand:
        raise ValueError("Brand not found.")

    allowed_fields = {"name", "description"}

    invalid_fields = set(updates.keys()) - allowed_fields

    if invalid_fields:
        raise ValueError(
            f"These fields cannot be updated: {', '.join(invalid_fields)}"
        )

    if "name" in updates:
        name = updates["name"].strip()

        if not name:
            raise ValueError("Brand name cannot be empty.")

        duplicate = (
            db.query(Brand)
            .filter(
                Brand.name == name,
                Brand.id != brand_id
            )
            .first()
        )

        if duplicate:
            raise ValueError("Another brand already uses this name.")

        updates["name"] = name

    if "description" in updates and updates["description"] is not None:
        updates["description"] = updates["description"].strip()

    try:
        for field, value in updates.items():
            setattr(brand, field, value)

        db.commit()
        db.refresh(brand)
        return brand

    except Exception:
        db.rollback()
        raise


def deactivate_brand(db: Session, brand_id: int):
    """Deactivate a brand without deleting its historical records."""

    brand = get_brand_by_id(db, brand_id)

    if not brand:
        raise ValueError("Brand not found.")

    brand.is_active = False

    try:
        db.commit()
        db.refresh(brand)
        return brand

    except Exception:
        db.rollback()
        raise
