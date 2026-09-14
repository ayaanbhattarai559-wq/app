import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from . import models, schemas


class NotFound(Exception):
    pass


class InsufficientStock(Exception):
    def __init__(self, label: str, available: int, requested: int):
        self.label = label
        self.available = available
        self.requested = requested
        super().__init__(f"{label}: requested {requested}, only {available} in stock")


def _product_query():
    return select(models.Product).options(selectinload(models.Product.variants))


# ---------- Categories ----------

def list_categories(db: Session):
    return db.execute(select(models.Category)).scalars().all()


def create_category(db: Session, data: schemas.CategoryCreate) -> models.Category:
    existing = db.get(models.Category, data.id)
    if existing:
        return existing
    cat = models.Category(id=data.id, label=data.label, is_custom=True)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


DEFAULT_CATEGORIES = [
    ("kurtas", "Kurtas"),
    ("shalwars", "Shalwars"),
    ("sarees", "Sarees"),
    ("formal", "Formal & Sherwanis"),
    ("casual", "Casual & Daily"),
    ("accessories", "Accessories"),
]


def seed_default_categories(db: Session) -> None:
    if db.execute(select(func.count(models.Category.id))).scalar_one() > 0:
        return
    for cid, label in DEFAULT_CATEGORIES:
        db.add(models.Category(id=cid, label=label, is_custom=False))
    db.commit()


# ---------- Products ----------

def list_products(db: Session, search: str | None = None, category: str | None = None):
    stmt = _product_query()
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (models.Product.name.ilike(like))
            | (models.Product.sku.ilike(like))
            | (models.Product.barcode.ilike(like))
        )
    if category:
        stmt = stmt.where(models.Product.category == category)
    stmt = stmt.order_by(models.Product.name)
    return db.execute(stmt).scalars().unique().all()


def get_product(db: Session, product_id: str, for_update: bool = False) -> models.Product:
    stmt = _product_query().where(models.Product.id == product_id)
    if for_update:
        stmt = stmt.with_for_update()
    product = db.execute(stmt).unique().scalar_one_or_none()
    if not product:
        raise NotFound(f"Product {product_id} not found")
    return product


def _resync_total_stock(product: models.Product) -> None:
    product.stock = sum(v.stock for v in product.variants)


def create_product(db: Session, data: schemas.ProductCreate) -> models.Product:
    payload = data.model_dump(exclude={"variants"})
    product = models.Product(**payload)
    for v in data.variants:
        product.variants.append(models.ProductVariant(
            id=v.id or f"{product.id or uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:6]}",
            color=v.color, size=v.size, stock=v.stock, sku=v.sku, barcode=v.barcode,
        ))
    _resync_total_stock(product)
    db.add(product)
    db.commit()
    db.refresh(product)
    return get_product(db, product.id)


def update_product(db: Session, product_id: str, data: schemas.ProductUpdate) -> models.Product:
    product = get_product(db, product_id)
    updates = data.model_dump(exclude_unset=True, exclude={"variants"})
    for field, value in updates.items():
        setattr(product, field, value)

    if data.variants is not None:
        # Edit flow replaces the whole variant list wholesale.
        existing_by_id = {v.id: v for v in product.variants}
        keep_ids = set()
        for v in data.variants:
            vid = v.id or f"{product_id}-{uuid.uuid4().hex[:6]}"
            keep_ids.add(vid)
            if vid in existing_by_id:
                ev = existing_by_id[vid]
                ev.color, ev.size, ev.stock = v.color, v.size, v.stock
                ev.sku, ev.barcode = v.sku, v.barcode
            else:
                product.variants.append(models.ProductVariant(
                    id=vid, color=v.color, size=v.size, stock=v.stock,
                    sku=v.sku, barcode=v.barcode,
                ))
        for v in list(product.variants):
            if v.id not in keep_ids:
                product.variants.remove(v)

    _resync_total_stock(product)
    db.commit()
    return get_product(db, product_id)


def delete_product(db: Session, product_id: str) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()


def _maybe_low_stock_notification(db: Session, product: models.Product, variant: models.ProductVariant | None) -> None:
    if variant is not None and variant.stock == 0:
        db.add(models.AppNotification(
            title=f"Depleted: Size {variant.size} - {product.name}",
            message=f"{variant.color} Size {variant.size} has just reached 0 units.",
            type="alert", read=False,
        ))
    if 0 <= product.stock <= product.low_stock_threshold:
        title = f"Out of Stock: {product.name}" if product.stock == 0 else f"Low Stock: {product.name}"
        db.add(models.AppNotification(
            title=title,
            message=f"{product.stock} units remaining across all sizes/colors.",
            type="alert", read=False,
        ))


def sell_variant(db: Session, product_id: str, variant_id: str) -> models.SaleTransaction:
    """Mirrors handleSoldVariant: sell exactly 1 unit of one color/size."""
    product = get_product(db, product_id, for_update=True)
    variant = next((v for v in product.variants if v.id == variant_id), None)
    if not variant:
        raise NotFound(f"Variant {variant_id} not found")
    if variant.stock <= 0:
        raise InsufficientStock(f"{product.name} ({variant.color}, {variant.size})", 0, 1)

    variant.stock -= 1
    _resync_total_stock(product)
    product.sold_count = (product.sold_count or 0) + 1

    unit_profit = float(product.price) - float(product.cost)
    tx = models.SaleTransaction(
        total_amount=float(product.price),
        total_cost=float(product.cost),
        total_profit=unit_profit,
        payment_method="contactless",
    )
    tx.items.append(models.SaleTransactionItem(
        product_id=product.id, product_name=product.name,
        sku=variant.sku or product.sku, color=variant.color, size=variant.size,
        quantity=1, unit_price=float(product.price), unit_cost=float(product.cost),
        subtotal=float(product.price), profit=unit_profit,
    ))
    db.add(tx)

    _maybe_low_stock_notification(db, product, variant)

    db.commit()
    db.refresh(tx)
    return tx


def restock_variant(db: Session, product_id: str, variant_id: str, amount: int) -> models.Product:
    product = get_product(db, product_id, for_update=True)
    variant = next((v for v in product.variants if v.id == variant_id), None)
    if not variant:
        raise NotFound(f"Variant {variant_id} not found")

    variant.stock += amount
    variant.last_restocked_at = datetime.utcnow()
    variant.last_restocked_amount = amount
    _resync_total_stock(product)

    entry = {
        "color": variant.color, "size": variant.size, "amount": amount,
        "timestamp": datetime.utcnow().isoformat(),
    }
    product.recent_restocks = ([entry] + list(product.recent_restocks or []))[:10]

    db.commit()
    return get_product(db, product_id)


def adjust_stock(db: Session, product_id: str, delta: int) -> models.Product:
    """Mirrors handleBatchAdjust: spread the delta proportionally across variants."""
    product = get_product(db, product_id, for_update=True)
    num_vars = len(product.variants) or 1
    var_delta = round(delta / num_vars)
    for v in product.variants:
        v.stock = max(0, v.stock + var_delta)
    _resync_total_stock(product)
    db.commit()
    return get_product(db, product_id)


def bulk_restock(db: Session, items: list[schemas.BulkRestockItem]) -> list[models.Product]:
    """Mirrors handleBulkRestockLowItems: distribute each product's amount evenly across its variants."""
    updated = []
    for item in items:
        product = get_product(db, item.product_id, for_update=True)
        num_vars = len(product.variants) or 1
        portion = math.ceil(item.amount / num_vars)
        now = datetime.utcnow()
        for v in product.variants:
            v.stock += portion
            v.last_restocked_at = now
            v.last_restocked_amount = portion
        _resync_total_stock(product)
        updated.append(product)
    db.commit()
    return [get_product(db, p.id) for p in updated]


# ---------- Sales / checkout ----------

def checkout(db: Session, data: schemas.CheckoutRequest) -> models.SaleTransaction:
    """Mirrors handleCompleteSale: multi-line cart, each line tied to a specific variant."""
    if not data.items:
        raise ValueError("Cart is empty")

    product_ids = sorted({i.product_id for i in data.items})
    products_by_id = {pid: get_product(db, pid, for_update=True) for pid in product_ids}

    total_amount = 0.0
    total_cost = 0.0
    tx = models.SaleTransaction(total_amount=0, total_cost=0, total_profit=0, payment_method=data.payment_method)

    for line in data.items:
        product = products_by_id[line.product_id]
        variant = next((v for v in product.variants if v.id == line.variant_id), None)
        if not variant:
            db.rollback()
            raise NotFound(f"Variant {line.variant_id} not found")
        if variant.stock < line.quantity:
            db.rollback()
            raise InsufficientStock(f"{product.name} ({variant.color}, {variant.size})", variant.stock, line.quantity)

        variant.stock -= line.quantity
        product.sold_count = (product.sold_count or 0) + line.quantity

        line_subtotal = float(product.price) * line.quantity
        line_cost = float(product.cost) * line.quantity
        total_amount += line_subtotal
        total_cost += line_cost

        tx.items.append(models.SaleTransactionItem(
            product_id=product.id, product_name=product.name,
            sku=variant.sku or product.sku, color=variant.color, size=variant.size,
            quantity=line.quantity, unit_price=float(product.price), unit_cost=float(product.cost),
            subtotal=line_subtotal, profit=line_subtotal - line_cost,
        ))

    for product in products_by_id.values():
        _resync_total_stock(product)

    tx.total_amount = round(total_amount, 2)
    tx.total_cost = round(total_cost, 2)
    tx.total_profit = round(total_amount - total_cost, 2)
    db.add(tx)

    for product in products_by_id.values():
        _maybe_low_stock_notification(db, product, None)

    db.commit()
    db.refresh(tx)
    return tx


def list_recent_sales(db: Session, limit: int = 50):
    stmt = select(models.SaleTransaction).order_by(
        models.SaleTransaction.timestamp.desc()
    ).limit(limit)
    return db.execute(stmt).scalars().unique().all()


# ---------- Purchase orders ----------

def list_purchase_orders(db: Session):
    stmt = select(models.PurchaseOrder).order_by(models.PurchaseOrder.created_at.desc())
    return db.execute(stmt).scalars().unique().all()


def create_purchase_order(db: Session, data: schemas.PurchaseOrderCreate) -> models.PurchaseOrder:
    count = db.execute(select(func.count(models.PurchaseOrder.id))).scalar() or 0
    po_number = f"PO-{1042 + count + 1}"

    po = models.PurchaseOrder(
        po_number=po_number, supplier_name=data.supplier_name,
        expected_date=data.expected_date, status="ordered",
    )
    total = 0.0
    for line in data.items:
        product = get_product(db, line.product_id)
        po.items.append(models.PurchaseOrderItem(
            product_id=product.id, product_name=product.name, sku=product.sku,
            quantity=line.quantity, unit_cost=line.unit_cost,
        ))
        total += line.quantity * line.unit_cost
    po.total_cost = round(total, 2)

    db.add(po)
    db.commit()
    db.refresh(po)
    return po


def receive_shipment(db: Session, po_id: str) -> models.PurchaseOrder:
    """Mirrors handleReceiveShipment: distribute each line's quantity evenly across the product's variants."""
    stmt = select(models.PurchaseOrder).where(models.PurchaseOrder.id == po_id)
    po = db.execute(stmt).scalar_one_or_none()
    if not po:
        raise NotFound(f"Purchase order {po_id} not found")
    if po.status == "received":
        return po

    now = datetime.utcnow()
    for line in po.items:
        product = get_product(db, line.product_id, for_update=True)
        num_vars = len(product.variants) or 1
        portion = math.ceil(line.quantity / num_vars)
        for v in product.variants:
            v.stock += portion
            v.last_restocked_at = now
            v.last_restocked_amount = portion
        _resync_total_stock(product)

    po.status = "received"
    db.add(models.AppNotification(
        title=f"Shipment Received ({po.po_number})",
        message=f"Goods received from {po.supplier_name}. Stock verified.",
        type="success", read=False,
    ))

    db.commit()
    db.refresh(po)
    return po


# ---------- Notifications ----------

def list_notifications(db: Session):
    stmt = select(models.AppNotification).order_by(models.AppNotification.created_at.desc())
    return db.execute(stmt).scalars().all()


def mark_all_read(db: Session) -> None:
    db.query(models.AppNotification).update({models.AppNotification.read: True})
    db.commit()


# ---------- Analytics ----------

def today_summary(db: Session) -> schemas.TodaySummary:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    row = db.execute(
        select(
            func.coalesce(func.sum(models.SaleTransactionItem.quantity), 0),
            func.coalesce(func.sum(models.SaleTransaction.total_amount), 0),
            func.coalesce(func.sum(models.SaleTransaction.total_cost), 0),
            func.coalesce(func.sum(models.SaleTransaction.total_profit), 0),
        )
        .select_from(models.SaleTransaction)
        .join(models.SaleTransactionItem)
        .where(models.SaleTransaction.timestamp >= today_start)
    ).first()
    units_sold, revenue, cost, profit = row

    low_stock_count = db.execute(
        select(func.count(models.Product.id)).where(
            models.Product.stock > 0,
            models.Product.stock <= models.Product.low_stock_threshold,
        )
    ).scalar_one()

    out_of_stock_count = db.execute(
        select(func.count(models.Product.id)).where(models.Product.stock == 0)
    ).scalar_one()

    return schemas.TodaySummary(
        units_sold=int(units_sold), revenue=float(revenue),
        cost=float(cost), profit=float(profit),
        low_stock_count=int(low_stock_count), out_of_stock_count=int(out_of_stock_count),
    )
