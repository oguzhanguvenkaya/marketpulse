"""
Barrel module — backward compatibility.

All endpoint logic has been split into:
  search_routes, product_routes, stats_routes,
  price_monitor_routes, seller_routes

This module re-assembles them into one ``router`` so that
``main.py`` (and any future consumer) can keep doing::

    from app.api.routes import router
"""

from fastapi import APIRouter

from app.api.search_routes import router as search_router
from app.api.product_routes import router as product_router
from app.api.stats_routes import router as stats_router
from app.api.price_monitor_routes import router as price_monitor_router
from app.api.seller_routes import router as seller_router

router = APIRouter()
router.include_router(search_router)
router.include_router(product_router)
router.include_router(stats_router)
router.include_router(price_monitor_router)
router.include_router(seller_router)
