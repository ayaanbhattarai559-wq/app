from datetime import datetime, date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

PaymentMethod = Literal["card", "cash", "contactless"]
POStatus = Literal["ordered", "shipped", "received"]
NotifType = Literal["alert", "success", "info"]


# ---------- Categories ----------

class CategoryCreate(BaseModel):
    id: str
    label: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    label: str
    is_custom: bool


# ---------- Product variants ----------

class VariantIn(BaseModel):
    id: Optional[str] = None  # client may supply a stable id; server generates one if absent
    color: str
    size: str
    stock: int = 0
    sku: Optional[str] = None
    barcode: Optional[str] = None


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    color: str
    size: str
    stock: int
    sku: Optional[str] = None
    barcode: Optional[str] = None
    last_restocked_at: Optional[datetime] = None
    last_restocked_amount: Optional[int] = None


# ---------- Products ----------

class ProductBase(BaseModel):
    sku: str
    barcode: Optional[str] = None
    name: str
    category: str
    category_label: str
    price: float
    cost: float
    low_stock_threshold: int = 5
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
    description: Optional[str] = None
    fabric: Optional[str] = None
    supplier: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)


class ProductCreate(ProductBase):
    variants: list[VariantIn] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    category_label: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    low_stock_threshold: Optional[int] = None
    image_url: Optional[str] = None
    image_alt: Optional[str] = None
    description: Optional[str] = None
    fabric: Optional[str] = None
    supplier: Optional[str] = None
    colors: Optional[list[str]] = None
    sizes: Optional[list[str]] = None
    # If provided, replaces the entire variant list (matches the edit-product modal's behavior)
    variants: Optional[list[VariantIn]] = None


class RecentRestockEntry(BaseModel):
    color: str
    size: str
    amount: int
    timestamp: datetime


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    stock: int
    sold_count: int = 0
    variants: list[VariantOut] = Field(default_factory=list)
    recent_restocks: list[RecentRestockEntry] = Field(default_factory=list)


class RestockVariantRequest(BaseModel):
    variant_id: str
    amount: int = Field(default=10, gt=0)


class AdjustRequest(BaseModel):
    delta: int  # positive or negative, spread proportionally across variants


class BulkRestockItem(BaseModel):
    product_id: str
    amount: int = Field(gt=0)


class BulkRestockRequest(BaseModel):
    items: list[BulkRestockItem]


class SellVariantRequest(BaseModel):
    variant_id: str


# ---------- Sales ----------

class SaleItemIn(BaseModel):
    product_id: str
    variant_id: str
    quantity: int = Field(gt=0)


class CheckoutRequest(BaseModel):
    items: list[SaleItemIn]
    payment_method: PaymentMethod


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    product_name: str
    sku: str
    color: Optional[str] = None
    size: Optional[str] = None
    quantity: int
    unit_price: float
    unit_cost: float
    subtotal: float
    profit: float


class SaleTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    timestamp: datetime
    total_amount: float
    total_cost: float
    total_profit: float
    payment_method: PaymentMethod
    items: list[SaleItemOut]


# ---------- Purchase Orders ----------

class POItemIn(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    unit_cost: float


class PurchaseOrderCreate(BaseModel):
    supplier_name: str
    expected_date: Optional[date] = None
    items: list[POItemIn]


class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: str
    product_name: str
    sku: str
    quantity: int
    unit_cost: float


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    po_number: str
    supplier_name: str
    created_at: datetime
    expected_date: Optional[date] = None
    status: POStatus
    total_cost: float
    items: list[POItemOut]


# ---------- Notifications ----------

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    message: str
    created_at: datetime
    type: NotifType
    read: bool


# ---------- Analytics ----------

class TodaySummary(BaseModel):
    units_sold: int
    revenue: float
    cost: float
    profit: float
    low_stock_count: int
    out_of_stock_count: int


TimeframePeriod = Literal["day", "week", "month", "year"]


class TimeSeriesPoint(BaseModel):
    id: str
    label: str
    sub_label: Optional[str] = None
    revenue: float
    cost: float
    profit: float
    units_sold: int
    highlight: bool = False
