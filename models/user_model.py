from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


# ── Auth / Role models ────────────────────────────────────────────────────────

ROLE_OWNER    = "owner"
ROLE_ADMIN    = "admin"
ROLE_DISPATCH = "dispatch"

@dataclass
class AppUser:
    id:           Optional[int] = None
    username:     str = ""
    password_hash:str = ""
    role:         str = ROLE_ADMIN   # owner | admin | dispatch
    full_name:    str = ""
    phone:        str = ""           # mobile number for OTP (with 91, no +)
    active:       bool = True
    created_at:   Optional[datetime] = None


# ── Business models ───────────────────────────────────────────────────────────

@dataclass
class Customer:
    id: Optional[int] = None

    name: str = ""
    phone: str = ""
    email: str = ""

    gst_no: str = ""
    pan_no: str = ""
    discount_percent: float = 0.0

    address_line1: str = ""   # street / village / locality
    district: str = ""
    state: str = ""
    pincode: str = ""

    created_at: Optional[datetime] = None

    @property
    def address(self) -> str:
        """Full address string for display."""
        parts = [
            p for p in [
                self.address_line1,
                self.district,
                self.state,
                self.pincode
            ] if p
        ]
        return ", ".join(parts)


@dataclass
class Plant:
    id:                  Optional[int] = None
    name:                str = ""
    category:            str = ""
    description:         str = ""
    unit_price:          float = 0.0
    stock_qty:           int = 0        # total individual plants
    low_stock_threshold: int = 10
    # Container / tray info
    container_type:      str = ""       # e.g. Tray, Bucket, Pot, None
    plants_per_unit:     int = 1        # how many plants per tray/bucket
    container_stock:     int = 0        # number of trays/buckets in stock
    created_at:          Optional[datetime] = None

    @property
    def is_low_stock(self) -> bool:
        return self.stock_qty <= self.low_stock_threshold

    @property
    def total_plants(self) -> int:
        """Total plants = loose stock + (containers × plants_per_unit)"""
        return self.stock_qty + (self.container_stock * self.plants_per_unit)


@dataclass
class Seed:
    id:                  Optional[int] = None
    name:                str = ""
    variety:             str = ""
    supplier:            str = ""
    quantity_grams:      float = 0.0    # stock in grams
    quantity_packets:    int = 0        # stock in packets
    grams_per_packet:    float = 0.0
    unit_price_gram:     float = 0.0    # price per gram
    unit_price_packet:   float = 0.0   # price per packet
    low_stock_grams:     float = 100.0  # alert threshold
    germination_rate:    float = 0.0    # % germination
    notes:               str = ""
    created_at:          Optional[datetime] = None

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_grams <= self.low_stock_grams


@dataclass
class Container:
    id:             Optional[int] = None
    name:           str = ""            # e.g. "50-Cell Tray", "10L Bucket"
    container_type: str = "Tray"        # Tray | Bucket | Pot | Box | Other
    capacity:       int = 0             # cells/plants it holds
    stock_qty:      int = 0             # how many we have
    unit_cost:      float = 0.0
    notes:          str = ""
    created_at:     Optional[datetime] = None


@dataclass
class OrderItem:
    id:                Optional[int] = None
    order_id:          Optional[int] = None
    production_lot_id: Optional[int] = None  # <-- Changed this line
    plant_name:        str = ""
    quantity:          int = 0
    unit_price:        float = 0.0
    plant_category:    str = ""

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

@dataclass
class Order:
    id:            Optional[int] = None
    customer_id:   Optional[int] = None
    customer_name: str = ""
    order_date:    Optional[datetime] = None
    status:        str = "Pending"
    notes:         str = ""
    total_amount:  float = 0.0
    items:         List[OrderItem] = field(default_factory=list)

    # delivery tracking
    delivery_status: str = "Pending"      # Pending | Out for Delivery | Delivered | Failed
    delivery_notes:  str = ""
    failure_reason:  str = ""
    delivered_at:    Optional[datetime] = None

    # fulfilment staff (filled by dispatch team)
    packed_by:       str = ""   # name of person who packed
    dispatched_by:   str = ""   # name of person who dispatched / driver
    received_by:     str = ""   # name of person who received at delivery

    STATUS_OPTIONS   = ["Pending", "Confirmed", "Dispatched", "Delivered", "Cancelled"]
    DELIVERY_OPTIONS = ["Pending", "Out for Delivery", "Delivered", "Failed"]


@dataclass
class Invoice:
    id:            Optional[int] = None
    order_id:      Optional[int] = None
    customer_name: str = ""
    invoice_date:  Optional[datetime] = None
    due_date:      Optional[datetime] = None
    paid:          bool = False
    paid_date:     Optional[datetime] = None
    notes:         str = ""
    total_amount:  float = 0.0
    discount_amount: float = 0.0
    price_override_notes: str = ""

# ── Production / Lot tracking models ─────────────────────────────────────────

STAGE_GERMINATION   = "Germination"
STAGE_TRANSPLANTING = "Transplanting"
STAGE_HARDENING     = "Hardening"
STAGE_SALE          = "Sale"
STAGE_SCRAP         = "Scrap"

STAGE_ORDER = [
    STAGE_GERMINATION,
    STAGE_TRANSPLANTING,
    STAGE_HARDENING,
    STAGE_SALE,
    STAGE_SCRAP,
]

STAGE_COLORS = {
    STAGE_GERMINATION:   "#1ABC9C",
    STAGE_TRANSPLANTING: "#2980B9",
    STAGE_HARDENING:     "#8E44AD",
    STAGE_SALE:          "#27AE60",
    STAGE_SCRAP:         "#C0392B",
}


@dataclass
class ProductionStage:
    id:             Optional[int] = None
    lot_id:         Optional[int] = None
    stage:          str = ""
    stage_date:     Optional[datetime] = None
    quantity_in:    int = 0
    quantity_out:   int = 0
    quantity_scrap: int = 0
    tray_count:     int = 0
    tray_type:      str = ""   # ✅ NEW FIELD
    location:       str = ""
    notes:          str = ""
    done_by:        str = ""
    created_at:     Optional[datetime] = None
    price:          float = 0.0



@dataclass
class ProductionLot:
    id: Optional[int] = None
    lot_number: str = ""
    plant_name: str = ""
    variety: str = ""
    seed_quantity: int = 0
    tray_count: int = 0
    plants_per_tray: int = 0
    tray_type: str = ""   # ✅ NEW FIELD
    location: str = ""
    created_by: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    current_stage: str = ""
    current_quantity: int = 0
    total_scrapped: int = 0




    @property
    def current_stage(self) -> str:
        if self.stages:
            return self.stages[-1].stage
        return STAGE_GERMINATION

    @property
    def current_quantity(self) -> int:
        """Live quantity = last stage quantity_out (or initial if no stages)."""
        if self.stages:
            last = self.stages[-1]
            return last.quantity_out if last.quantity_out > 0 else last.quantity_in
        return self.quantity

    @property
    def total_scrapped(self) -> int:
        return sum(s.quantity_scrap for s in self.stages)

    @property
    def is_in_inventory(self) -> bool:
        """Lot appears in inventory once it reaches Hardening stage."""
        return self.current_stage in (STAGE_HARDENING, STAGE_SALE)


@dataclass
class ProductionScrap:
    id:          Optional[int] = None
    lot_id:      Optional[int] = None
    stage_id:    Optional[int] = None
    quantity:    int = 0
    reason:      str = ""
    scrap_date:  Optional[datetime] = None
    notes:       str = ""
    recorded_by: str = ""
