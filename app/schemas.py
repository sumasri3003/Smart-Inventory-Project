# 
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal

# -------- SUPPLIERS --------
class SupplierCreate(BaseModel):
    name: str
    contact: Optional[str] = None
    region: Optional[str] = None


class SupplierOut(SupplierCreate):
    supplier_id: int

    class Config:
        orm_mode = True


# -------- PRODUCTS --------
class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: float
    supplier_id: Optional[int] = None


class ProductOut(ProductCreate):
    product_id: int

    class Config:
        orm_mode = True


# -------- WAREHOUSES --------
class WarehouseCreate(BaseModel):
    code: str
    name: str
    location: Optional[str] = None
    capacity: Optional[int] = None
    manager: Optional[str] = None
    region: Optional[str] = None


class WarehouseOut(WarehouseCreate):
    warehouse_id: int

    class Config:
        orm_mode = True


# -------- INVENTORY --------
class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int


class InventoryOut(InventoryCreate):
    inventory_id: int
    last_updated: Optional[str] = None

    class Config:
        orm_mode = True


# -------- ORDERS --------
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderCreate(BaseModel):
    warehouse_id: int
    items: List[OrderItemCreate]

class OrderItemOut(OrderItemCreate):
    order_item_id: int

    class Config:
        orm_mode = True

class OrderOut(BaseModel):
    order_id: int
    warehouse_id: int
    status: str
    items: List[OrderItemOut]

    class Config:
        orm_mode = True