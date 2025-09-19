"""Database base configuration."""

from typing import Any
from sqlalchemy.orm import declarative_base

# Base class for all SQLAlchemy models
Base: Any = declarative_base()
