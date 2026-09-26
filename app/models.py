import uuid
from datetime import datetime

from sqlalchemy import (
    String, Integer, Numeric, Boolean, Text, ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    label: Mapped[str] = mapped_column(String(150))
    is_custom: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: _uid("prod"))
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60))  # references Category.id, loosely (custom cats allowed)
    category_label: Mapped[str] = mapped_column(String(150))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    cost: Mapped[float] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)  # denormalized sum of variant stocks
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    sold_count: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_alt: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    fabric: Mapped[str | None] = mapped_column(String(150), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    colors: Mapped[list] = mapped_column(JSON, default=list)
    sizes: Mapped[list] = mapped_column(JSON, default=list)
      # Last 10 restock events, newest first: [{color, size, amount, timestamp}, ...]
    recent_restocks: Mapped[list] = mapped_column(JSON, default=list)
    # Last 10 manual stock adjustments, newest first: [{delta, reason, note, timestamp}, ...]
    recent_adjustments: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    color: Mapped[str] = mapped_column(String(60))
    size: Mapped[str] = mapped_column(String(20))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[str | None] = mapped_column(String(60), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_restocked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_restocked_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="variants")


class SaleTransaction(Base):
    __tablename__ = "sale_transactions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: _uid("tx"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_profit: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    payment_method: Mapped[str] = mapped_column(String(20))

    items: Mapped[list["SaleTransactionItem"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class SaleTransactionItem(Base):
    __tablename__ = "sale_transaction_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("sale_transactions.id"))
    # Nullable + ON DELETE SET NULL: deleting a product must never delete its
    # sale history. product_name/sku below are a snapshot taken at sale time,
    # so the receipt still reads correctly even after the product is gone.
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))  # actual price charged (after discount)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2))
    profit: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    list_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # price before discount
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    # Cumulative units already returned for this line, so partial returns are
    # supported and the same units can never be returned twice.
    returned_quantity: Mapped[int] = mapped_column(Integer, default=0)

    transaction: Mapped["SaleTransaction"] = relationship(back_populates="items")
class SaleReturn(Base):
    __tablename__ = "sale_returns"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: _uid("ret"))
    transaction_id: Mapped[str] = mapped_column(ForeignKey("sale_transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    refund_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    restocked: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list["SaleReturnItem"]] = relationship(
        back_populates="return_", cascade="all, delete-orphan"
    )


class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[str] = mapped_column(ForeignKey("sale_returns.id"))
    sale_item_id: Mapped[int] = mapped_column(ForeignKey("sale_transaction_items.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(60), nullable=True)
    size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    refund_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    reason: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    return_: Mapped["SaleReturn"] = relationship(back_populates="items")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: _uid("po"))
    po_number: Mapped[str] = mapped_column(String(40), unique=True)
    supplier_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expected_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ordered")
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    po_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"))
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_name: Mapped[str] = mapped_column(String(200))
    sku: Mapped[str] = mapped_column(String(60))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2))

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")


class AppNotification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: _uid("notif"))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    type: Mapped[str] = mapped_column(String(20))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
