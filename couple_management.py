#!/usr/bin/env python3
"""
Couple Mirror (Espejo Fantasma) - FASE 2 Backend
Synchronized dual-questionnaire with blind response collection & friction mapping.
Magic tokens + ORM models for couple_sessions, couple_answers, couple_reports.
"""

import secrets
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple, List
from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, Enum as SQLEnum, Index, create_engine, event, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
Base = declarative_base()

# ============ ENUMS ============

class CoupleStatus(str, Enum):
    """Estados de una sesión de pareja"""
    PENDING = "pending"              # Esperando que User B se una
    MATCHED = "matched"              # Ambos registrados, al menos uno respondió
    COMPLETED = "completed"          # Ambos completaron (500 preguntas cada uno)


# ============ ORM MODELS ============

class CoupleSession(Base):
    """
    Sesión de pareja - coordina respuestas de dos usuarios con tokens mágicos.

    ARQUITECTURA:
    - User A inicia: couple_id generado, magic_token_a generado
    - magic_token_b compartible con User B (72h TTL)
    - Al validar token B, User B se registra en couple_sessions
    - Cuando ambos completan 500q → status=completed, trigger auto-generación PDF

    SEGURIDAD:
    - Tokens: secrets.token_urlsafe(48) = 64 chars, base64url-safe
    - TTL: 72 horas (configurable)
    - No hay registro/password - solo tokens
    """
    __tablename__ = "couple_sessions"
    __table_args__ = (
        Index("idx_couple_id", "couple_id"),
        Index("idx_user_a_id", "user_a_id"),
        Index("idx_magic_token_a", "magic_token_a"),
        Index("idx_magic_token_b", "magic_token_b"),
        Index("idx_status", "status"),
    )

    # Identificadores
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    couple_id = Column(String(36), unique=True, index=True, nullable=False)

    # Usuarios
    user_a_id = Column(String(100), nullable=False, index=True)
    user_a_name = Column(String(255), nullable=False)
    user_a_email = Column(String(255), nullable=False)

    user_b_id = Column(String(100), nullable=True, index=True)  # NULL hasta validar token
    user_b_name = Column(String(255), nullable=True)
    user_b_email = Column(String(255), nullable=True)

    # Magic tokens (72h TTL)
    magic_token_a = Column(String(64), unique=True, index=True, nullable=False)
    magic_token_b = Column(String(64), unique=True, index=True, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)  # 72h from creation

    # Status y timestamps
    status = Column(SQLEnum(CoupleStatus), default=CoupleStatus.PENDING, index=True)
    user_a_completed_at = Column(DateTime, nullable=True)  # Timestamp cuando A termina Q500
    user_b_completed_at = Column(DateTime, nullable=True)  # Timestamp cuando B termina Q500

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def is_token_valid(self, token: str) -> bool:
        """Valida si un token (A o B) es válido y no expiró"""
        if datetime.utcnow() > self.token_expires_at:
            return False
        return token == self.magic_token_a or token == self.magic_token_b

    def is_both_completed(self) -> bool:
        """Retorna True si ambos usuarios completaron sus 500 preguntas"""
        return self.user_a_completed_at is not None and self.user_b_completed_at is not None

    def __repr__(self):
        return f"<CoupleSession({self.couple_id}, {self.status.value})>"


class CoupleAnswers(Base):
    """
    Almacenamiento de respuestas pareadas (500 preguntas × 2 usuarios).

    ESTRUCTURA:
    - Cada usuario guarda sus 500 respuestas como JSON: {q1: 2, q2: 4, ...q500: 3}
    - Respuestas abiertas encriptadas igual que OpenAnswerRecord (AES-256-GCM)
    - Metadata: IP, user-agent, timestamp

    SEGURIDAD:
    - Datos encriptados per-couple-id (similar a per-user en OpenAnswerRecord)
    - Validación de token mágico antes de guardar
    """
    __tablename__ = "couple_answers"
    __table_args__ = (
        Index("idx_couple_id", "couple_id"),
        Index("idx_couple_user", "couple_id", "user_id"),
        Index("idx_submitted_at", "submitted_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    couple_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(1), nullable=False)  # 'a' o 'b'

    # Respuestas (Q1-Q500): {q1: 1-5, q2: 1-5, ..., q500: 1-5}
    answers_json = Column(JSON, nullable=False)

    # Respuestas abiertas encriptadas (OP1-OP3): {encrypted_op1: "ciphertext|nonce", ...}
    open_answers_encrypted = Column(JSON, nullable=True)

    # Metadata para audit trail
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CoupleAnswers({self.couple_id}, user_{self.user_id})>"


class CoupleReport(Base):
    """
    Reporte dual generado automaticamente cuando ambos usuarios completaron.

    ESTRUCTURA:
    - Almacena ruta del PDF generado + metadata de visualizaciones
    - Generated timestamp para auditoría
    - Metadata contiene datos para regeneración (radar_data, heatmap_deltas, etc.)

    FLUJO:
    1. User B completa Q500
    2. check_completion() → True
    3. Trigger async generate_couple_report()
    4. Crear CoupleReport entry + almacenar PDF
    """
    __tablename__ = "couple_reports"
    __table_args__ = (
        Index("idx_couple_id", "couple_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    couple_id = Column(String(36), unique=True, nullable=False, index=True)
    user_a_id = Column(String(100), nullable=False)
    user_b_id = Column(String(100), nullable=False)

    # PDF storage
    pdf_path = Column(String(500), nullable=False)  # Ruta relativa: reports/couple_{couple_id}.pdf
    pdf_data = Column(Text, nullable=True)  # Base64-encoded PDF si se necesita BLOB

    # Metadata para regeneración
    visualization_metadata = Column(JSON, default=dict)  # {radar_data, heatmap_deltas, timeline_data, gap_cards}

    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CoupleReport({self.couple_id})>"


# ============ SERVICE CLASS ============

class CoupleService:
    """
    Business logic para sesiones de pareja.
    Encapsula: token generation, validation, status checks, DB operations.
    """

    TOKEN_TTL_HOURS = 72

    @staticmethod
    def generate_magic_tokens() -> Tuple[str, str]:
        """
        Genera dos tokens mágicos (A y B) seguros.

        Returns:
            (token_a, token_b): Dos strings de 64 chars base64url-safe
        """
        token_a = secrets.token_urlsafe(48)  # 64 chars
        token_b = secrets.token_urlsafe(48)
        return token_a, token_b

    @staticmethod
    def initiate_couple_session(
        session: Session,
        user_email_a: str,
        user_name_a: str,
        couple_email_b: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Paso 1: User A inicia sesión de pareja.

        Args:
            session: SQLAlchemy session
            user_email_a: Email de User A
            user_name_a: Nombre de User A
            couple_email_b: Email de User B (opcional, para auto-envío)

        Returns:
            (couple_id, magic_token_a, magic_token_b)

        Raises:
            ValueError: Si falta información crítica
        """
        if not user_email_a or not user_name_a:
            raise ValueError("user_email_a y user_name_a son requeridos")

        couple_id = str(uuid.uuid4())
        user_a_id = f"user_{uuid.uuid4().hex[:8]}"
        token_a, token_b = CoupleService.generate_magic_tokens()
        token_expires = datetime.utcnow() + timedelta(hours=CoupleService.TOKEN_TTL_HOURS)

        couple_session = CoupleSession(
            couple_id=couple_id,
            user_a_id=user_a_id,
            user_a_name=user_name_a,
            user_a_email=user_email_a,
            magic_token_a=token_a,
            magic_token_b=token_b,
            token_expires_at=token_expires,
            status=CoupleStatus.PENDING
        )

        try:
            session.add(couple_session)
            session.commit()
            logger.info(f"CoupleSession created: {couple_id}")
            return couple_id, token_a, token_b
        except IntegrityError as e:
            session.rollback()
            logger.error(f"IntegrityError creating CoupleSession: {e}")
            raise ValueError(f"Error creando sesión de pareja: {str(e)}")

    @staticmethod
    def validate_token(session: Session, token: str) -> Optional[CoupleSession]:
        """
        Valida un token mágico y retorna la sesión de pareja.

        Args:
            session: SQLAlchemy session
            token: Magic token (A o B)

        Returns:
            CoupleSession si el token es válido, None si expiró o no existe
        """
        couple = session.query(CoupleSession).filter(
            (CoupleSession.magic_token_a == token) | (CoupleSession.magic_token_b == token)
        ).first()

        if not couple:
            return None

        if datetime.utcnow() > couple.token_expires_at:
            logger.warning(f"Token expirado para couple_id {couple.couple_id}")
            return None

        return couple

    @staticmethod
    def register_user_b(
        session: Session,
        couple_id: str,
        user_b_id: str,
        user_b_name: str,
        user_b_email: str
    ) -> bool:
        """
        Paso 2: User B se registra con su token.

        Args:
            session: SQLAlchemy session
            couple_id: ID de la sesión de pareja
            user_b_id: ID del usuario B
            user_b_name: Nombre del usuario B
            user_b_email: Email del usuario B

        Returns:
            True si se registró, False si error
        """
        try:
            couple = session.query(CoupleSession).filter_by(couple_id=couple_id).first()
            if not couple:
                return False

            couple.user_b_id = user_b_id
            couple.user_b_name = user_b_name
            couple.user_b_email = user_b_email
            couple.status = CoupleStatus.MATCHED
            couple.updated_at = datetime.utcnow()

            session.commit()
            logger.info(f"User B registered for couple_id {couple_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error registering User B: {e}")
            return False

    @staticmethod
    def save_couple_answers(
        session: Session,
        couple_id: str,
        user_id: str,  # 'a' o 'b'
        answers: Dict,
        open_answers_encrypted: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Paso 3: User A o B guarda sus 500 respuestas.

        Args:
            session: SQLAlchemy session
            couple_id: ID de la sesión
            user_id: 'a' o 'b'
            answers: Dict {q1: 2, q2: 3, ..., q500: 5}
            open_answers_encrypted: Dict {encrypted_op1: "...", encrypted_op2: "...", ...}
            ip_address: IP del cliente
            user_agent: User-Agent del navegador

        Returns:
            True si se guardó, False si error
        """
        try:
            couple_answers = CoupleAnswers(
                couple_id=couple_id,
                user_id=user_id,
                answers_json=answers,
                open_answers_encrypted=open_answers_encrypted,
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.add(couple_answers)

            # Marcar timestamp de completitud en CoupleSession
            couple = session.query(CoupleSession).filter_by(couple_id=couple_id).first()
            if couple:
                if user_id == 'a':
                    couple.user_a_completed_at = datetime.utcnow()
                elif user_id == 'b':
                    couple.user_b_completed_at = datetime.utcnow()
                couple.updated_at = datetime.utcnow()

            session.commit()
            logger.info(f"Answers saved for couple_id {couple_id}, user {user_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving couple answers: {e}")
            return False

    @staticmethod
    def check_completion(session: Session, couple_id: str) -> bool:
        """
        Verifica si ambos usuarios completaron sus respuestas.

        Args:
            session: SQLAlchemy session
            couple_id: ID de la sesión

        Returns:
            True si ambos completaron, False si falta alguno
        """
        couple = session.query(CoupleSession).filter_by(couple_id=couple_id).first()
        if not couple:
            return False

        is_complete = couple.is_both_completed()

        if is_complete and couple.status != CoupleStatus.COMPLETED:
            couple.status = CoupleStatus.COMPLETED
            couple.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Couple {couple_id} marked as COMPLETED")

        return is_complete

    @staticmethod
    def get_couple_session(session: Session, couple_id: str) -> Optional[CoupleSession]:
        """Obtiene una sesión de pareja por ID"""
        return session.query(CoupleSession).filter_by(couple_id=couple_id).first()

    @staticmethod
    def get_couple_answers(session: Session, couple_id: str, user_id: Optional[str] = None) -> List[CoupleAnswers]:
        """Obtiene respuestas de una sesión de pareja (ambas si user_id=None)"""
        query = session.query(CoupleAnswers).filter_by(couple_id=couple_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()
