from __future__ import annotations

from collections import Counter

ORDERS = [
    {"id": "ORD-1001", "date": "2026-03-12", "product": "Thermo Bottle", "brand": "Nord", "status": "delivered", "total": 4200, "returned": False},
    {"id": "ORD-1002", "date": "2026-03-13", "product": "Travel Mug", "brand": "Nord", "status": "delivered", "total": 2500, "returned": False},
    {"id": "ORD-1003", "date": "2026-03-13", "product": "Desk Lamp", "brand": "Luma", "status": "returned", "total": 3800, "returned": True},
    {"id": "ORD-1004", "date": "2026-03-14", "product": "Notebook Set", "brand": "Paperlane", "status": "processing", "total": 1600, "returned": False},
    {"id": "ORD-1005", "date": "2026-03-15", "product": "Storage Box", "brand": "Fold", "status": "cancelled", "total": 2900, "returned": False},
    {"id": "ORD-1006", "date": "2026-03-16", "product": "Desk Lamp", "brand": "Luma", "status": "delivered", "total": 3800, "returned": False},
]

PRODUCTS = [
    {"sku": "SKU-001", "name": "Thermo Bottle", "brand": "Nord", "stock": 18, "margin_pct": 31},
    {"sku": "SKU-002", "name": "Travel Mug", "brand": "Nord", "stock": 7, "margin_pct": 22},
    {"sku": "SKU-003", "name": "Desk Lamp", "brand": "Luma", "stock": 5, "margin_pct": -4},
    {"sku": "SKU-004", "name": "Notebook Set", "brand": "Paperlane", "stock": 42, "margin_pct": 19},
    {"sku": "SKU-005", "name": "Storage Box", "brand": "Fold", "stock": 9, "margin_pct": 13},
]


def compute_dashboard_metrics() -> dict:
    gross_revenue = sum(order["total"] for order in ORDERS if order["status"] != "cancelled")
    # Intentionally simple current logic. A future backlog task can harden return handling.
    net_revenue = sum(order["total"] for order in ORDERS if order["status"] == "delivered")
    delivered_orders = [order for order in ORDERS if order["status"] == "delivered"]
    return_rate = round(
        len([order for order in ORDERS if order["returned"]]) / max(len(delivered_orders), 1) * 100,
        1,
    )
    low_stock = [product for product in PRODUCTS if product["stock"] <= 10]
    top_products = Counter(order["product"] for order in delivered_orders).most_common(3)
    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "return_rate": return_rate,
        "low_stock": low_stock,
        "top_products": top_products,
        "order_count": len(ORDERS),
    }


def list_orders() -> list[dict]:
    return sorted(ORDERS, key=lambda order: order["date"], reverse=True)


def list_products() -> list[dict]:
    return sorted(PRODUCTS, key=lambda product: product["stock"])
