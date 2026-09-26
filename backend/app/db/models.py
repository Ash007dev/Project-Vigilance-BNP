from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    transaction_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    sender_account: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    sender_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    sender_customer_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    receiver_account: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    receiver_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    receiver_customer_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    sender_customer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    receiver_customer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    currency: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    channel: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    crypto_flag: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    crypto_wallet: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )