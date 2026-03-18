from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from services.pet_app.domain import compute_dashboard_metrics, list_orders, list_products

app = FastAPI(title="Seller Desk")
templates = Jinja2Templates(directory="services/pet_app/templates")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    context = {
        "request": request,
        "page": "dashboard",
        "metrics": compute_dashboard_metrics(),
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@app.get("/orders", response_class=HTMLResponse)
def orders(request: Request) -> HTMLResponse:
    context = {
        "request": request,
        "page": "orders",
        "orders": list_orders(),
    }
    return templates.TemplateResponse(request, "orders.html", context)


@app.get("/products", response_class=HTMLResponse)
def products(request: Request) -> HTMLResponse:
    context = {
        "request": request,
        "page": "products",
        "products": list_products(),
    }
    return templates.TemplateResponse(request, "products.html", context)
