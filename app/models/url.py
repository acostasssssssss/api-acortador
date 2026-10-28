"""
Modelos de base de datos desacoplados con soporte de timezone:
- Destination: la URL real de destino
- Slug: el nombre corto editable
- Click: analytics de redirecciones
- DestinationHistory: historial de cambios de destino
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Boolean, ForeignKey, Integer, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Destination(Base):
    """URL de destino real. Independiente del slug."""
    __tablename__ = "destinations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    slugs = relationship("Slug", back_populates="destination", lazy="selectin")
    history = relationship("DestinationHistory", back_populates="destination", lazy="selectin")


class Slug(Base):
    """
    Slug editable que apunta a un Destination.
    El código (slug) es mutable; el ID es inmutable (preserva analytics).
    """
    __tablename__ = "slugs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(64), unique=True, nullable=False, index=True)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    edit_token = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    redirect_type = Column(String(3), default="307", nullable=False)  # 301 o 307
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    destination = relationship("Destination", back_populates="slugs", lazy="selectin")
    owner = relationship("User", back_populates="slugs", lazy="selectin")
    clicks = relationship("Click", back_populates="slug", lazy="selectin")
    slug_history = relationship("SlugHistory", back_populates="slug", lazy="selectin")

    __table_args__ = (
        Index("ix_slugs_code_active", "code", "is_active"),
        Index("ix_slugs_user_active", "user_id", "is_active"),
    )


class SlugHistory(Base):
    """Historial de cambios de slug (renombrados)."""
    __tablename__ = "slug_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug_id = Column(UUID(as_uuid=True), ForeignKey("slugs.id", ondelete="CASCADE"), nullable=False)
    old_code = Column(String(64), nullable=False)
    new_code = Column(String(64), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    slug = relationship("Slug", back_populates="slug_history")


class DestinationHistory(Base):
    """Historial de cambios de URL destino."""
    __tablename__ = "destination_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = Column(
        UUID(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False
    )
    old_target_url = Column(Text, nullable=False)
    new_target_url = Column(Text, nullable=False)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    destination = relationship("Destination", back_populates="history")


class Click(Base):
    """Registro de cada redirección (analytics)."""
    __tablename__ = "clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug_id = Column(UUID(as_uuid=True), ForeignKey("slugs.id", ondelete="CASCADE"), nullable=False)
    clicked_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ip_hash = Column(String(64), nullable=True)  # Hash del IP (anónimo)
    user_agent = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    country = Column(String(2), nullable=True)  # Código ISO

    slug = relationship("Slug", back_populates="clicks")

    __table_args__ = (
        Index("ix_clicks_slug_id_clicked_at", "slug_id", "clicked_at"),
    )