from backend.database import get_connection
from models.user_model import Customer, Plant, Order, OrderItem, Invoice
from typing import List, Optional
from datetime import datetime


# ─── Customer Service ────────────────────────────────────────────────────────

class CustomerService:

    @staticmethod
    def _row_to_customer(row) -> Customer:
        return Customer(
            id=row[0],
            name=row[1] or "",
            phone=row[2] or "",
            email=row[3] or "",

            gst_no=row[4] or "",
            pan_no=row[5] or "",
            discount_percent=float(row[6] or 0),

            address_line1=row[7] or "",
            district=row[8] or "",
            state=row[9] or "",
            pincode=row[10] or "",

            created_at=row[11]
        )

    @staticmethod
    def get_all() -> List[Customer]:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    email,
                    COALESCE(gst_no,''),
                    COALESCE(pan_no,''),
                    COALESCE(discount_percent,0),
                    COALESCE(address_line1,''),
                    COALESCE(district,''),
                    COALESCE(state,''),
                    COALESCE(pincode,''),
                    created_at
                FROM customers
                ORDER BY name
            """)

            return [
                CustomerService._row_to_customer(r)
                for r in cur.fetchall()
            ]

    @staticmethod
    def search(query: str) -> List[Customer]:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    id,
                    name,
                    phone,
                    email,
                    COALESCE(gst_no,''),
                    COALESCE(pan_no,''),
                    COALESCE(discount_percent,0),
                    COALESCE(address_line1,''),
                    COALESCE(district,''),
                    COALESCE(state,''),
                    COALESCE(pincode,''),
                    created_at
                FROM customers
                WHERE
                    name ILIKE %s OR
                    phone ILIKE %s OR
                    email ILIKE %s OR
                    gst_no ILIKE %s OR
                    pan_no ILIKE %s OR
                    address_line1 ILIKE %s OR
                    district ILIKE %s OR
                    state ILIKE %s OR
                    pincode ILIKE %s
                ORDER BY name
            """, (f"%{query}%",) * 9)

            return [
                CustomerService._row_to_customer(r)
                for r in cur.fetchall()
            ]

    @staticmethod
    def save(c: Customer) -> Customer:
        with get_connection() as conn:
            cur = conn.cursor()

            if c.id:
                cur.execute("""
                    UPDATE customers
                    SET
                        name=%s,
                        phone=%s,
                    email=%s,
                    gst_no=%s,
                    pan_no=%s,
                    discount_percent=%s,
                    address_line1=%s,
                    district=%s,
                    state=%s,
                        pincode=%s
                    WHERE id=%s
                """, (
                    c.name,
                    c.phone,
                    c.email,
                    c.gst_no,
                    c.pan_no,
                    c.discount_percent,
                    c.address_line1,
                    c.district,
                    c.state,
                    c.pincode,
                    c.id
                ))

            else:
                cur.execute("""
                    INSERT INTO customers (
                        name,
                        phone,
                        email,
                        gst_no,
                        pan_no,
                        discount_percent,
                        address_line1,
                        district,
                        state,
                        pincode
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, (
                    c.name,
                    c.phone,
                    c.email,
                    c.gst_no,
                    c.pan_no,
                    c.discount_percent,
                    c.address_line1,
                    c.district,
                    c.state,
                    c.pincode
                ))

                c.id = cur.fetchone()[0]

        return c

    @staticmethod
    def delete(customer_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM customers WHERE id=%s",
                (customer_id,)
            )


# ─── Plant / Inventory Service ───────────────────────────────────────────────

class PlantService:
    @staticmethod
    def get_all() -> List[Plant]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, category, description, unit_price, stock_qty,
                       low_stock_threshold,
                       COALESCE(container_type,''), COALESCE(plants_per_unit,1),
                       COALESCE(container_stock,0), created_at
                FROM plants ORDER BY name
            """)
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append(Plant(
                    id=row[0], name=row[1], category=row[2] or "",
                    description=row[3] or "", unit_price=float(row[4] or 0),
                    stock_qty=int(row[5] or 0), low_stock_threshold=int(row[6] or 10),
                    container_type=row[7] or "", plants_per_unit=int(row[8] or 1),
                    container_stock=int(row[9] or 0), created_at=row[10]
                ))
            return result

    @staticmethod
    def search(query: str) -> List[Plant]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, category, description, unit_price, stock_qty,
                       low_stock_threshold,
                       COALESCE(container_type,''), COALESCE(plants_per_unit,1),
                       COALESCE(container_stock,0), created_at
                FROM plants WHERE name ILIKE %s OR category ILIKE %s ORDER BY name
            """, (f"%{query}%", f"%{query}%"))
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append(Plant(
                    id=row[0], name=row[1], category=row[2] or "",
                    description=row[3] or "", unit_price=float(row[4] or 0),
                    stock_qty=int(row[5] or 0), low_stock_threshold=int(row[6] or 10),
                    container_type=row[7] or "", plants_per_unit=int(row[8] or 1),
                    container_stock=int(row[9] or 0), created_at=row[10]
                ))
            return result

    @staticmethod
    def save(p: Plant) -> Plant:
        with get_connection() as conn:
            cur = conn.cursor()
            if p.id:
                cur.execute("""
                    UPDATE plants SET name=%s, category=%s, description=%s, unit_price=%s,
                    stock_qty=%s, low_stock_threshold=%s, container_type=%s,
                    plants_per_unit=%s, container_stock=%s WHERE id=%s
                """, (
                    p.name, p.category, p.description, p.unit_price, p.stock_qty,
                    p.low_stock_threshold, p.container_type, p.plants_per_unit,
                    p.container_stock, p.id
                ))
            else:
                cur.execute("""
                    INSERT INTO plants (
                        name, category, description, unit_price, stock_qty,
                        low_stock_threshold, container_type, plants_per_unit,
                        container_stock
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (
                    p.name, p.category, p.description, p.unit_price, p.stock_qty,
                    p.low_stock_threshold, p.container_type, p.plants_per_unit,
                    p.container_stock
                ))
                p.id = cur.fetchone()[0]
        return p

    @staticmethod
    def update_stock(plant_id: int, qty_change: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE plants SET stock_qty = stock_qty + %s WHERE id=%s", (qty_change, plant_id))

    @staticmethod
    def delete(plant_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM plants WHERE id=%s", (plant_id,))

    @staticmethod
    def get_low_stock() -> List[Plant]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, category, description, unit_price, stock_qty, low_stock_threshold, created_at
                FROM plants WHERE stock_qty <= low_stock_threshold ORDER BY stock_qty
            """)
            return [Plant(*row) for row in cur.fetchall()]


# ─── Order Service ───────────────────────────────────────────────────────────

class ProductionLotService:
    @staticmethod
    def get_hardened_inventory():
        from backend.database import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            # Explicitly join with production_stages to get the stage price
            cur.execute("""
                SELECT 
                    pl.id, 
                    pl.plant_name, 
                    pl.category, 
                    COALESCE(ps.price, 0) AS unit_price,
                    pl.quantity
                FROM production_lots pl
                LEFT JOIN (
                    SELECT lot_id, MAX(price) AS price 
                    FROM production_stages 
                    WHERE stage = 'hardening' 
                    GROUP BY lot_id
                ) ps ON pl.id = ps.lot_id
                WHERE pl.quantity > 0
                ORDER BY pl.plant_name
            """)

            class HardenedPlant:
                def __init__(self, id, name, category, unit_price, stock_qty):
                    self.id = id
                    self.name = name
                    self.category = category
                    self.unit_price = float(unit_price or 0.0)
                    self.stock_qty = int(stock_qty or 0)

            return [HardenedPlant(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]


class OrderService:
    @staticmethod
    def _row_to_order_item(row) -> OrderItem:
        return OrderItem(
            id=row[0],
            order_id=row[1],
            production_lot_id=row[2],  # Changed from plant_id
            plant_name=row[3] or "",
            quantity=int(row[4] or 0),
            unit_price=float(row[5] or 0),
            plant_category=row[6] or "",
        )

    @staticmethod
    def get_all() -> List[Order]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                    SELECT o.id, o.customer_id, c.name, o.order_date, o.status, o.notes, o.total_amount,
                           COALESCE(o.delivery_status,'Pending'), COALESCE(o.delivery_notes,''),
                           COALESCE(o.failure_reason,''), o.delivered_at,
                           COALESCE(o.packed_by,''), COALESCE(o.dispatched_by,''), COALESCE(o.received_by,'')
                    FROM orders o LEFT JOIN customers c ON o.customer_id=c.id ORDER BY o.order_date DESC
                """)
            result = []
            for row in cur.fetchall():
                o = Order(
                    id=row[0], customer_id=row[1], customer_name=row[2] or "",
                    order_date=row[3], status=row[4] or "Pending",
                    notes=row[5] or "", total_amount=float(row[6] or 0),
                    delivery_status=row[7] or "Pending",
                    delivery_notes=row[8] or "",
                    failure_reason=row[9] or "",
                    delivered_at=row[10],
                    packed_by=row[11] or "",
                    dispatched_by=row[12] or "",
                    received_by=row[13] or "",
                )
                result.append(o)

            if result:
                order_by_id = {o.id: o for o in result}
                cur.execute("""
                        SELECT oi.id, oi.order_id, oi.production_lot_id,
                               COALESCE(pl.plant_name, ''), oi.quantity, oi.unit_price,
                               COALESCE(pl.category, '')
                        FROM order_items oi
                        LEFT JOIN production_lots pl ON oi.production_lot_id = pl.id
                        WHERE oi.order_id = ANY(%s)
                        ORDER BY oi.id
                    """, (list(order_by_id.keys()),))

                for item_row in cur.fetchall():
                    item = OrderService._row_to_order_item(item_row)
                    order = order_by_id.get(item.order_id)
                    if order:
                        order.items.append(item)

                # RECALCULATE TOTAL AFTER LOADING ITEMS
                for o in result:
                    if o.items:
                        o.total_amount = sum(item.quantity * item.unit_price for item in o.items)

            return result
    @staticmethod
    def get_by_id(order_id: int) -> Optional[Order]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT o.id, o.customer_id, c.name, o.order_date, o.status, o.notes, o.total_amount,
                       COALESCE(o.delivery_status,'Pending'), COALESCE(o.delivery_notes,''),
                       COALESCE(o.failure_reason,''), o.delivered_at,
                       COALESCE(o.packed_by,''), COALESCE(o.dispatched_by,''), COALESCE(o.received_by,'')
                FROM orders o LEFT JOIN customers c ON o.customer_id=c.id WHERE o.id=%s
            """, (order_id,))
            row = cur.fetchone()
            if not row:
                return None
            order = Order(
                id=row[0], customer_id=row[1], customer_name=row[2] or "",
                order_date=row[3], status=row[4] or "Pending",
                notes=row[5] or "", total_amount=float(row[6] or 0),
                delivery_status=row[7] or "Pending",
                delivery_notes=row[8] or "",
                failure_reason=row[9] or "",
                delivered_at=row[10],
                packed_by=row[11] or "",
                dispatched_by=row[12] or "",
                received_by=row[13] or "",
            )
            # FIXED: Join with production_lots instead of plants
            cur.execute("""
                SELECT oi.id, oi.order_id, oi.production_lot_id,
                       COALESCE(pl.plant_name, ''), oi.quantity, oi.unit_price,
                       COALESCE(pl.category, '')
                FROM order_items oi
                LEFT JOIN production_lots pl ON oi.production_lot_id = pl.id
                WHERE oi.order_id=%s
                ORDER BY oi.id
            """, (order_id,))
            order.items = [OrderService._row_to_order_item(r) for r in cur.fetchall()]
            return order


    @staticmethod
    def save(order: Order) -> Order:
        with get_connection() as conn:
            cur = conn.cursor()

            # Calculate total based on what was passed to the function
            total = sum(i.quantity * i.unit_price for i in order.items)

            if order.id:
                cur.execute("""
                        UPDATE orders SET customer_id=%s, status=%s, notes=%s, total_amount=%s 
                        WHERE id=%s
                    """, (order.customer_id, order.status, order.notes, total, order.id))
                cur.execute("DELETE FROM order_items WHERE order_id=%s", (order.id,))
            else:
                cur.execute("""
                        INSERT INTO orders (customer_id, status, notes, total_amount)
                        VALUES (%s,%s,%s,%s) RETURNING id
                    """, (order.customer_id, order.status, order.notes, total))
                order.id = cur.fetchone()[0]

            for item in order.items:
                # Save the explicitly provided unit_price (this is the key fix)
                cur.execute("""
                        INSERT INTO order_items (order_id, production_lot_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                    """, (order.id, item.production_lot_id, item.quantity, item.unit_price))

                # Update inventory
                cur.execute("UPDATE production_lots SET quantity = quantity - %s WHERE id=%s",
                            (item.quantity, item.production_lot_id))

            order.total_amount = total
        return order


    @staticmethod
    def update_status(order_id: int, status: str):
        with get_connection() as conn:
            cur = conn.cursor()

            # 1. Fetch the current status before making changes
            cur.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
            row = cur.fetchone()
            if not row:
                return

            current_status = row[0]

            # If the status isn't actually changing, do nothing
            if current_status == status:
                return

                # 2. Update the order to the new status
            cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))

            # 3. Handle Inventory Adjustments
            if status == 'Cancelled' and current_status != 'Cancelled':
                # Order is being cancelled: RESTORE stock
                cur.execute("""
                        SELECT production_lot_id, quantity 
                        FROM order_items 
                        WHERE order_id=%s
                    """, (order_id,))

                for lot_id, qty in cur.fetchall():
                    cur.execute("""
                            UPDATE production_lots 
                            SET quantity = quantity + %s 
                            WHERE id = %s
                        """, (qty, lot_id))

            elif current_status == 'Cancelled' and status != 'Cancelled':
                # Order is being un-cancelled (e.g., set back to Pending): RE-DEDUCT stock
                cur.execute("""
                        SELECT production_lot_id, quantity 
                        FROM order_items 
                        WHERE order_id=%s
                    """, (order_id,))

                for lot_id, qty in cur.fetchall():
                    cur.execute("""
                            UPDATE production_lots 
                            SET quantity = quantity - %s 
                            WHERE id = %s
                        """, (qty, lot_id))

    @staticmethod
    def update_invoice_pricing(order_id: int, item_prices: dict[int, float]) -> float:
        with get_connection() as conn:
            cur = conn.cursor()
            for item_id, unit_price in item_prices.items():
                cur.execute(
                    "UPDATE order_items SET unit_price=%s WHERE id=%s AND order_id=%s",
                    (unit_price, item_id, order_id),
                )
            cur.execute("SELECT COALESCE(SUM(subtotal),0) FROM order_items WHERE order_id=%s", (order_id,))
            total = float(cur.fetchone()[0] or 0)
            cur.execute("UPDATE orders SET total_amount=%s WHERE id=%s", (total, order_id))
            return total

    @staticmethod
    def update_delivery(order_id: int, delivery_status: str, delivery_notes: str,
                        failure_reason: str, packed_by: str = "",
                        dispatched_by: str = "", received_by: str = ""):
        from datetime import datetime
        with get_connection() as conn:
            cur = conn.cursor()
            delivered_at = datetime.now() if delivery_status == "Delivered" else None
            cur.execute("""
                UPDATE orders
                SET delivery_status=%s, delivery_notes=%s, failure_reason=%s,
                    delivered_at=%s, packed_by=%s, dispatched_by=%s, received_by=%s
                WHERE id=%s
            """, (delivery_status, delivery_notes, failure_reason,
                  delivered_at, packed_by, dispatched_by, received_by, order_id))

    @staticmethod
    def update_logistics(order_id: int, delivery_status: str, packed_by: str,
                         dispatched_by: str, received_by: str,
                         delivery_notes: str, failure_reason: str):
        """Updates the delivery tracking and fulfilment staff fields."""
        query = """
            UPDATE orders 
            SET delivery_status = %s,
                packed_by = %s,
                dispatched_by = %s,
                received_by = %s,
                delivery_notes = %s,
                failure_reason = %s,
                delivered_at = CASE 
                                   WHEN %s = 'Delivered' THEN CURRENT_TIMESTAMP 
                                   ELSE delivered_at 
                               END
            WHERE id = %s
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    delivery_status, packed_by, dispatched_by, received_by,
                    delivery_notes, failure_reason, delivery_status, order_id
                ))
# ─── Invoice Service ─────────────────────────────────────────────────────────

class InvoiceService:
    @staticmethod
    def create_for_order(order_id: int, discount_amount: float = 0.0,
                         price_override_notes: str = "") -> Invoice:
        from datetime import date, timedelta
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM invoices WHERE order_id=%s", (order_id,))
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE invoices
                    SET discount_amount=%s, price_override_notes=%s
                    WHERE id=%s
                """, (discount_amount, price_override_notes, existing[0]))
                inv_id = existing[0]
            else:
                due = date.today() + timedelta(days=30)
                cur.execute("""
                    INSERT INTO invoices (order_id, due_date, discount_amount, price_override_notes)
                    VALUES (%s,%s,%s,%s) RETURNING id
                """, (order_id, due, discount_amount, price_override_notes))
                inv_id = cur.fetchone()[0]
        return InvoiceService.get_by_id(inv_id)

    @staticmethod
    def get_all() -> List[Invoice]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT i.id, i.order_id, c.name, i.invoice_date, i.due_date,
                       i.paid, i.paid_date, i.notes,
                       GREATEST(o.total_amount - COALESCE(i.discount_amount,0), 0) AS total_amount,
                       COALESCE(i.discount_amount,0), COALESCE(i.price_override_notes,'')
                FROM invoices i
                JOIN orders o ON i.order_id=o.id
                JOIN customers c ON o.customer_id=c.id
                ORDER BY i.invoice_date DESC
            """)
            return [Invoice(*row) for row in cur.fetchall()]

    @staticmethod
    def get_by_id(invoice_id: int) -> Optional[Invoice]:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT i.id, i.order_id, c.name, i.invoice_date, i.due_date,
                       i.paid, i.paid_date, i.notes,
                       GREATEST(o.total_amount - COALESCE(i.discount_amount,0), 0) AS total_amount,
                       COALESCE(i.discount_amount,0), COALESCE(i.price_override_notes,'')
                FROM invoices i
                JOIN orders o ON i.order_id=o.id
                JOIN customers c ON o.customer_id=c.id
                WHERE i.id=%s
            """, (invoice_id,))
            row = cur.fetchone()
            return Invoice(*row) if row else None

    @staticmethod
    def mark_paid(invoice_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE invoices SET paid=TRUE, paid_date=CURRENT_TIMESTAMP WHERE id=%s
            """, (invoice_id,))


# ── Seed Service ──────────────────────────────────────────────────────────────
class SeedService:
    @staticmethod
    def get_all():
        from models.user_model import Seed
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id,name,variety,supplier,quantity_grams,quantity_packets,
                       grams_per_packet,unit_price_gram,unit_price_packet,
                       low_stock_grams,germination_rate,notes,created_at
                FROM seeds ORDER BY name
            """)
            return [Seed(*r) for r in cur.fetchall()]

    @staticmethod
    def search(query: str):
        from models.user_model import Seed
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id,name,variety,supplier,quantity_grams,quantity_packets,
                       grams_per_packet,unit_price_gram,unit_price_packet,
                       low_stock_grams,germination_rate,notes,created_at
                FROM seeds WHERE name ILIKE %s OR variety ILIKE %s OR supplier ILIKE %s
                ORDER BY name
            """, (f"%{query}%",)*3)
            return [Seed(*r) for r in cur.fetchall()]

    @staticmethod
    def save(s):
        from models.user_model import Seed
        with get_connection() as conn:
            cur = conn.cursor()
            if s.id:
                cur.execute("""
                    UPDATE seeds SET name=%s,variety=%s,supplier=%s,
                    quantity_grams=%s,quantity_packets=%s,grams_per_packet=%s,
                    unit_price_gram=%s,unit_price_packet=%s,low_stock_grams=%s,
                    germination_rate=%s,notes=%s WHERE id=%s
                """, (s.name,s.variety,s.supplier,s.quantity_grams,s.quantity_packets,
                      s.grams_per_packet,s.unit_price_gram,s.unit_price_packet,
                      s.low_stock_grams,s.germination_rate,s.notes,s.id))
            else:
                cur.execute("""
                    INSERT INTO seeds (name,variety,supplier,quantity_grams,quantity_packets,
                    grams_per_packet,unit_price_gram,unit_price_packet,low_stock_grams,
                    germination_rate,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """, (s.name,s.variety,s.supplier,s.quantity_grams,s.quantity_packets,
                      s.grams_per_packet,s.unit_price_gram,s.unit_price_packet,
                      s.low_stock_grams,s.germination_rate,s.notes))
                s.id = cur.fetchone()[0]
        return s

    @staticmethod
    def add_stock(seed_id: int, grams: float = 0, packets: int = 0):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE seeds SET
                  quantity_grams   = quantity_grams   + %s,
                  quantity_packets = quantity_packets + %s
                WHERE id=%s
            """, (grams, packets, seed_id))

    @staticmethod
    def remove_stock(seed_id: int, grams: float = 0, packets: int = 0):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE seeds SET
                  quantity_grams   = GREATEST(0, quantity_grams   - %s),
                  quantity_packets = GREATEST(0, quantity_packets - %s)
                WHERE id=%s
            """, (grams, packets, seed_id))

    @staticmethod
    def delete(seed_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM seeds WHERE id=%s", (seed_id,))


# ── Container Service ─────────────────────────────────────────────────────────
class ContainerService:
    @staticmethod
    def get_all():
        from models.user_model import Container
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id,name,container_type,capacity,stock_qty,unit_cost,notes,created_at
                FROM containers ORDER BY container_type,name
            """)
            return [Container(*r) for r in cur.fetchall()]

    @staticmethod
    def add_stock(container_id: int, qty: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE containers SET stock_qty=stock_qty+%s WHERE id=%s",
                        (qty, container_id))

    @staticmethod
    def remove_stock(container_id: int, qty: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE containers SET stock_qty=GREATEST(0,stock_qty-%s) WHERE id=%s",
                        (qty, container_id))

    @staticmethod
    def save(c):
        from models.user_model import Container
        with get_connection() as conn:
            cur = conn.cursor()
            if c.id:
                cur.execute("""
                    UPDATE containers SET name=%s,container_type=%s,capacity=%s,
                    stock_qty=%s,unit_cost=%s,notes=%s WHERE id=%s
                """, (c.name,c.container_type,c.capacity,c.stock_qty,c.unit_cost,c.notes,c.id))
            else:
                cur.execute("""
                    INSERT INTO containers (name,container_type,capacity,stock_qty,unit_cost,notes)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
                """, (c.name,c.container_type,c.capacity,c.stock_qty,c.unit_cost,c.notes))
                c.id = cur.fetchone()[0]
        return c

    @staticmethod
    def delete(container_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM containers WHERE id=%s", (container_id,))


# ── Production Service ────────────────────────────────────────────────────────

class ProductionService:

    # ── Lot number generator ──────────────────────────────────────────────────
    @staticmethod
    def next_lot_number() -> str:
        """Generate next unique lot number like LOT-2025-0042"""
        from datetime import datetime as dt
        year = dt.now().year
        with get_connection() as conn:
            cur = conn.cursor()
            # Find how many lots exist for this year to generate the next number
            cur.execute(
                "SELECT COUNT(*) FROM production_lots WHERE lot_number LIKE %s",
                (f"LOT-{year}-%",)
            )
            count = cur.fetchone()[0]
        return f"LOT-{year}-{count + 1:04d}"

    # ── Create new lot (1st Entry) ────────────────────────────────────────────
    @staticmethod
    def create_lot(lot) -> "ProductionLot":
        """lot is a ProductionLot dataclass instance (id=None)."""
        with get_connection() as conn:
            cur = conn.cursor()

            # Safely handle seed_id in case the frontend doesn't supply it
            seed_id = getattr(lot, 'seed_id', None)

            cur.execute("""
                INSERT INTO production_lots
                    (lot_number, plant_name, category, seed_id, quantity,
                     tray_count, plants_per_tray, tray_type, seed_quantity,
                     location, created_by, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (
                lot.lot_number,
                lot.plant_name,
                lot.variety,  # Maps frontend 'variety' to DB 'category'
                seed_id,  # Safely falls back to None
                lot.quantity,
                lot.tray_count,
                lot.plants_per_tray,
                lot.tray_type,  # New frontend addition
                lot.seed_quantity,  # New frontend addition
                lot.location,
                lot.created_by,
                lot.notes
            ))
            lot.id = cur.fetchone()[0]
        return lot

    # ── Advance to next stage ─────────────────────────────────────────────────
    @staticmethod
    def add_stage(stage):
        """Add a production stage only. Hardening will stay here for processing."""
        with get_connection() as conn:
            cur = conn.cursor()

            # Safely get price (defaults to 0.0 if not provided)
            price = getattr(stage, 'price', 0.0)

            cur.execute("""
                INSERT INTO production_stages (
                    lot_id, stage, stage_date, quantity_in, quantity_out, 
                    quantity_scrap, tray_count, location, notes, done_by, price
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                stage.lot_id, stage.stage, stage.stage_date, stage.quantity_in,
                stage.quantity_out, stage.quantity_scrap, stage.tray_count,
                stage.location, stage.notes, stage.done_by, stage.price  # <-- Make sure this is here!
            ))

            stage.id = cur.fetchone()[0]

        return stage

    # ── Handle Custom Processing (NEW) ────────────────────────────────────────
    @staticmethod
    def record_processing(lot_id: int, process_name: str, quantity: int, done_by: str, notes: str = ""):
        """
        New method to support the 'Process' button on the Hardening tab.
        This allows you to log specific actions (e.g., 'Grading', 'Pruning')
        without moving the lot to a new stage.
        """
        with get_connection() as conn:
            cur = conn.cursor()

            # Note: You will need to create a 'production_processing_logs' table
            # in your database to utilize this.
            cur.execute("""
                INSERT INTO production_processing_logs (
                    lot_id, process_name, quantity_processed, done_by, notes, process_date
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, (lot_id, process_name, quantity, done_by, notes))

            log_id = cur.fetchone()[0]

        return log_id

    @staticmethod
    def _sync_to_inventory(lot_id: int, quantity: int, unit_price: float = 0.0,
                           tray_count: int = 0):
        """When a lot reaches Hardening, add/update entry in plants table."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT plant_name, category, COALESCE(tray_type,''), COALESCE(plants_per_tray,1)
                FROM production_lots WHERE id=%s
            """, (lot_id,))
            row = cur.fetchone()
            if not row:
                return
            plant_name, category, tray_type, lot_plants_per_tray = row
            category = category or ""
            tray_type = tray_type or "Tray"
            quantity = int(quantity or 0)
            tray_count = int(tray_count or 0)
            if tray_count > 0:
                plants_per_unit = max(1, quantity // tray_count)
                loose_remainder = max(0, quantity - (plants_per_unit * tray_count))
            else:
                plants_per_unit = int(lot_plants_per_tray or 1)
                loose_remainder = quantity

            # Check if plant already exists
            cur.execute(
                """
                SELECT id, stock_qty
                FROM plants
                WHERE name=%s AND COALESCE(category, '')=%s
                """,
                (plant_name, category)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute("""
                    UPDATE plants
                    SET stock_qty = stock_qty + %s,
                        unit_price = CASE WHEN %s > 0 THEN %s ELSE unit_price END,
                        container_type = CASE WHEN %s > 0 THEN %s ELSE container_type END,
                        plants_per_unit = CASE WHEN %s > 0 THEN %s ELSE plants_per_unit END,
                        container_stock = COALESCE(container_stock, 0) + %s
                    WHERE id=%s
                """, (
                    loose_remainder,
                    unit_price, unit_price,
                    tray_count, tray_type,
                    tray_count, plants_per_unit,
                    tray_count,
                    existing[0],
                ))
            else:
                cur.execute("""
                    INSERT INTO plants (
                        name, category, unit_price, stock_qty, low_stock_threshold,
                        container_type, plants_per_unit, container_stock
                    )
                    VALUES (%s, %s, %s, %s, 10, %s, %s, %s)
                """, (
                    plant_name, category, unit_price, loose_remainder,
                    tray_type if tray_count > 0 else "",
                    plants_per_unit,
                    tray_count,
                ))

    # ── Record scrap ──────────────────────────────────────────────────────────
    @staticmethod
    def record_scrap(lot_id: int, stage_id, quantity: int, reason: str,
                     notes: str = "", recorded_by: str = ""):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO production_scrap
                    (lot_id, stage_id, quantity, reason, notes, recorded_by)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (lot_id, stage_id, quantity, reason, notes, recorded_by))

    # ── Queries ───────────────────────────────────────────────────────────────
    @staticmethod
    def get_all_lots(stage_filter: str = "") -> list:
        from models.user_model import ProductionLot
        with get_connection() as conn:
            cur = conn.cursor()
            if stage_filter:
                cur.execute("""
                    SELECT DISTINCT pl.id, pl.lot_number, pl.plant_name, pl.category,
                           pl.seed_id, pl.quantity, pl.tray_count, pl.plants_per_tray,
                           pl.tray_type, pl.seed_quantity, pl.location,
                           pl.created_by, pl.notes, pl.created_at
                    FROM production_lots pl
                    JOIN production_stages ps ON ps.lot_id = pl.id
                    WHERE ps.stage = %s
                    AND ps.id = (
                        SELECT MAX(id) FROM production_stages WHERE lot_id = pl.id
                    )
                    ORDER BY pl.created_at DESC
                """, (stage_filter,))
            else:
                cur.execute("""
                    SELECT id, lot_number, plant_name, category, seed_id, quantity,
                           tray_count, plants_per_tray, tray_type, seed_quantity,
                           location, created_by, notes, created_at
                    FROM production_lots ORDER BY created_at DESC
                """)
            lots = []
            for row in cur.fetchall():
                lots.append(ProductionLot(
                    id=row[0], lot_number=row[1], plant_name=row[2],
                    variety=row[3], seed_id=row[4], quantity=row[5],
                    tray_count=row[6], plants_per_tray=row[7],
                    tray_type=row[8] if len(row) > 8 else "",
                    seed_quantity=row[9] if len(row) > 9 else 0,
                    location=row[10] if len(row) > 10 else "",
                    created_by=row[11] if len(row) > 11 else "",
                    notes=row[12] if len(row) > 12 else "",
                    created_at=row[13] if len(row) > 13 else None
                ))
            return lots


    @staticmethod
    @staticmethod
    def get_lot_with_stages(lot_id: int):
        from models.user_model import ProductionLot, ProductionStage
        from backend.database import get_connection

        with get_connection() as conn:
            cur = conn.cursor()

            # 1. Fetch the main Lot information
            cur.execute("""
                        SELECT id, lot_number, plant_name, category, seed_id, quantity, 
                               tray_count, plants_per_tray, tray_type, seed_quantity, 
                               location, created_by, notes, created_at
                        FROM production_lots 
                        WHERE id = %s
                    """, (lot_id,))

            lot_row = cur.fetchone()
            if not lot_row:
                return None

            lot = ProductionLot(
                id=lot_row[0],
                lot_number=lot_row[1],
                plant_name=lot_row[2],
                variety=lot_row[3],  # <--- THE FIX IS HERE: Changed 'category' back to 'variety'
                seed_id=lot_row[4],
                quantity=lot_row[5],
                tray_count=lot_row[6],
                plants_per_tray=lot_row[7],
                tray_type=lot_row[8],
                seed_quantity=lot_row[9],
                location=lot_row[10],
                created_by=lot_row[11],
                notes=lot_row[12],
                created_at=lot_row[13]
            )

            # 2. Fetch the Stages history (WITH THE NEW PRICE COLUMN)
            cur.execute("""
                        SELECT id, lot_id, stage, stage_date, quantity_in, quantity_out, 
                               quantity_scrap, tray_count, location, notes, done_by, 
                               created_at, price 
                        FROM production_stages 
                        WHERE lot_id = %s
                        ORDER BY stage_date ASC
                    """, (lot_id,))

            stages = []
            for row in cur.fetchall():
                stage = ProductionStage(
                    id=row[0],
                    lot_id=row[1],
                    stage=row[2],
                    stage_date=row[3],
                    quantity_in=row[4],
                    quantity_out=row[5],
                    quantity_scrap=row[6],
                    tray_count=row[7],
                    location=row[8],
                    notes=row[9],
                    done_by=row[10],
                    created_at=row[11],
                    price=row[12] if row[12] is not None else 0.0
                )
                stages.append(stage)

            lot.stages = stages
            return lot

    @staticmethod
    def get_scrap_for_lot(lot_id: int) -> list:
        from models.user_model import ProductionScrap
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, lot_id, stage_id, quantity, reason,
                       scrap_date, notes, recorded_by
                FROM production_scrap WHERE lot_id=%s ORDER BY scrap_date DESC
            """, (lot_id,))
            return [ProductionScrap(
                id=r[0], lot_id=r[1], stage_id=r[2], quantity=r[3],
                reason=r[4], scrap_date=r[5], notes=r[6], recorded_by=r[7]
            ) for r in cur.fetchall()]

    @staticmethod
    def delete_lot(lot_id: int):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM production_lots WHERE id=%s", (lot_id,))
