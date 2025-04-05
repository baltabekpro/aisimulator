from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging
import json

from core.db.models.ai_partner import AIPartner
from core.services.base import BaseService

logger = logging.getLogger(__name__)

class AIPartnerService(BaseService):
    """Service for AI Partner operations."""
    
    def __init__(self, db: Session):
        logger.info("Initializing AIPartnerService")
        super().__init__(AIPartner, db)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[AIPartner]:
        """
        Get all AI partners with enhanced logging for debugging.
        
        Args:
            skip: Number of items to skip for pagination
            limit: Maximum number of items to return
            
        Returns:
            List of AI partners
        """
        try:
            logger.info(f"Fetching AI partners with skip={skip}, limit={limit}")
            
            # Log table info for debugging
            from sqlalchemy import inspect
            inspector = inspect(self.db.bind)
            tables = inspector.get_table_names()
            
            if 'ai_partners' not in tables:
                logger.error(f"ai_partners table not found in database. Available tables: {tables}")
                return []
                
            # Direct query with explicit table
            query = self.db.query(AIPartner)
            result = query.offset(skip).limit(limit).all()
            
            logger.info(f"Found {len(result)} AI partners")
            for partner in result:
                logger.info(f"Partner {partner.name} with ID {partner.partner_id}")
                
            return result
        except Exception as e:
            logger.exception(f"Error retrieving AI partners: {e}")
            return []
    
    def get(self, id: Any) -> Optional[AIPartner]:
        """
        Get an AI partner by ID with enhanced error handling.
        
        Args:
            id: The ID of the AI partner
            
        Returns:
            AI partner or None if not found
        """
        logger.info(f"Getting AI partner with ID: {id}")
        try:
            # Convert string ID to UUID if needed
            partner_id = UUID(id) if isinstance(id, str) else id
            
            # Query directly by partner_id
            partner = self.db.query(AIPartner).filter(AIPartner.partner_id == partner_id).first()
            
            if partner:
                logger.info(f"Found partner: {partner.name}")
            else:
                logger.warning(f"No partner found with ID: {id}")
                
            return partner
        except Exception as e:
            logger.exception(f"Error getting AI partner with ID {id}: {e}")
            return None
    
    def create_partner(self, user_id: UUID, name: str, age: int, biography: str = None, 
                      personality: Dict[str, Any] = None) -> AIPartner:
        """
        Create a new AI partner.
        
        Args:
            user_id: User ID
            name: Partner name
            age: Partner age
            biography: Optional biography
            personality: Optional personality traits and interests
            
        Returns:
            Created AI partner
        """
        logger.info(f"Creating new AI partner: {name}")
        
        # Convert personality to JSON string if it's a dict
        personality_json = json.dumps(personality) if isinstance(personality, dict) else personality
        
        partner_data = {
            "user_id": user_id,
            "name": name,
            "age": age,
            "biography": biography,
            "personality": personality_json
        }
        
        # Create the partner
        partner = self.create(obj_in=partner_data)
        logger.info(f"Created AI partner {name} with ID: {partner.partner_id}")
        
        return partner
