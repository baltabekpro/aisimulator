from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import uuid

from core.db.base_class import Base

# Fix: Define the TypeVar with a string type bound instead of variable reference
ModelType = TypeVar("ModelType")  # Simplified TypeVar definition

logger = logging.getLogger(__name__)

class BaseService(Generic[ModelType]):
    """
    Base class for all services with common CRUD operations.
    """
    
    def __init__(self, model: Type[Any], db: Session):
        """
        Initialize the base service.
        
        Args:
            model: The SQLAlchemy model class
            db: SQLAlchemy database session
        """
        self.model = model
        self.db = db
    
    def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        """
        try:
            # Handle UUID conversion if needed
            if isinstance(id, str):
                try:
                    id = uuid.UUID(id)
                except ValueError:
                    # If not a valid UUID, continue with string ID
                    pass
            
            # Find primary key column name
            pk_name = self.model.__table__.primary_key.columns.keys()[0]
            
            # Create filter for primary key
            filter_dict = {pk_name: id}
            return self.db.query(self.model).filter_by(**filter_dict).first()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__} with ID {id}: {e}")
            return None
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get multiple records with pagination.
        """
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving {self.model.__name__} records: {e}")
            # Return empty list instead of raising exception
            return []
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        """
        try:
            db_obj = self.model(**obj_in)  # type: ignore
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise
    
    def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        Update a record.
        """
        try:
            db_obj = self.get(id)
            if (db_obj is None):
                return None
                
            for field in obj_in:
                if hasattr(db_obj, field):
                    setattr(db_obj, field, obj_in[field])
            
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} with ID {id}: {e}")
            raise
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record.
        """
        try:
            db_obj = self.get(id)
            if db_obj is None:
                return False
                
            self.db.delete(db_obj)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with ID {id}: {e}")
            raise
