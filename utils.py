"""Utility functions."""

import logging

logger = logging.getLogger(__name__)

def validate_search_query(query: str) -> bool:
    """Validate search query."""
    return len(query.strip()) > 1 and len(query) <= 100

async def log_user_action(user_id: int, action: str):
    """Log user actions."""
    logger.info(f"User {user_id}: {action}")