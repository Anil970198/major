from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ── DB location:  app/data/emails.db  ───────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_URL = f"sqlite:///{DATA_DIR / 'emails.db'}"

engine = create_engine(DB_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

# ──────────────────────────────── MODELS ────────────────────────────────────────

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    gmail_id = Column(String, unique=True, nullable=False)
    from_addr = Column(String)
    to_addr = Column(String)
    subject = Column(String)
    snippet = Column(Text)
    body = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    triage_label = Column(String)
    triage_subtype = Column(String)
    draft_reply = Column(Text)
    meeting_url = Column(Text)
    sent = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Email(id={self.id}, subject={self.subject})>"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)
    content = Column(Text)
    due_time = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Reminder(id={self.id}, due_time={self.due_time})>"


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    recipient = Column(String)
    title = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    calendar_url = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Meeting(id={self.id}, title={self.title}, start={self.start_time})>"


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    recipient = Column(String)
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SentEmail(id={self.id}, recipient={self.recipient})>"

# ────────────────────────────── INIT & SESSION ──────────────────────────────────

def init_db() -> None:
    """Run at startup to ensure all tables exist."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Session:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ────────────────────────────── HELPERS ─────────────────────────────────────────

def upsert_email(data: dict) -> None:
    with session_scope() as db:
        row = db.query(Email).filter_by(gmail_id=data["gmail_id"]).one_or_none()
        if row is None:
            db.add(Email(**data))
        else:
            row.triage_label = data.get("triage_label", row.triage_label)
            row.snippet = data.get("snippet", row.snippet)
            row.body = data.get("body", row.body)
            row.timestamp = data.get("timestamp", row.timestamp)


def update_draft(gmail_id: str, text: str) -> None:
    with session_scope() as db:
        row = db.query(Email).filter_by(gmail_id=gmail_id).one_or_none()
        if row:
            row.draft_reply = text


def mark_sent(gmail_id: str) -> None:
    with session_scope() as db:
        row = db.query(Email).filter_by(gmail_id=gmail_id).one_or_none()
        if row:
            row.sent = True


def save_meeting(gmail_id: str, link: str) -> None:
    with session_scope() as db:
        row = db.query(Email).filter_by(gmail_id=gmail_id).one_or_none()
        if row:
            row.meeting_url = link


def add_reminder(email_id: int, content: str, due_time: datetime) -> None:
    with session_scope() as db:
        db.add(Reminder(email_id=email_id, content=content, due_time=due_time))


def log_meeting(email_id: int, recipient: str, title: str, start: datetime, end: datetime, url: str) -> None:
    with session_scope() as db:
        db.add(Meeting(email_id=email_id, recipient=recipient, title=title,
                       start_time=start, end_time=end, calendar_url=url))


def log_sent_email(email_id: int, recipient: str, subject: str, body: str) -> None:
    with session_scope() as db:
        db.add(SentEmail(email_id=email_id, recipient=recipient, subject=subject, body=body))

