"""Demo adapter — implements BrandAdapter using in-memory mock data.

Wraps the existing toc_mock_data module to provide backward-compatible
demo mode. In production, brands implement their own adapter with
HTTP calls to their backend API.
"""

from __future__ import annotations

from .brand_adapter import BrandAdapter
from .brand_config import BrandConfig
from . import toc_mock_data as _data


class DemoAdapter(BrandAdapter):
    """Mock data adapter for demo/development. Delegates to toc_mock_data."""

    def __init__(self, config: BrandConfig):
        self.config = config
        self._default_user = config.default_user_id

    # --- Discovery ---

    def campaign_calendar(self, month: str | None = None) -> list[dict]:
        return _data.campaign_calendar(month)

    def available_coupons(self) -> list[dict]:
        return _data.available_coupons()

    def claim_all_coupons(self, user_id: str) -> dict:
        return _data.claim_all_coupons(user_id)

    # --- Account ---

    def get_current_user(self, user_id: str) -> dict | None:
        return _data.get_current_user(user_id)

    def my_account(self, user_id: str) -> dict | None:
        return _data.my_account(user_id)

    def my_coupons(self, user_id: str, status: str | None = None) -> list[dict]:
        return _data.my_coupons(user_id, status=status)

    def my_orders(self, user_id: str, limit: int = 10) -> list[dict]:
        return _data.my_orders(user_id, limit=limit)

    # --- Menu ---

    def nearby_stores(self, city: str | None = None, keyword: str | None = None) -> list[dict]:
        return _data.nearby_stores(city=city, keyword=keyword)

    def store_detail(self, store_id: str) -> dict | None:
        return _data.store_detail(store_id)

    def browse_menu(self, store_id: str) -> dict:
        return _data.browse_menu(store_id)

    def drink_detail(self, product_code: str) -> dict | None:
        return _data.drink_detail(product_code)

    def nutrition_info(self, product_code: str) -> dict | None:
        return _data.nutrition_info(product_code)

    # --- Stars Mall ---

    def stars_mall_products(self, category: str | None = None) -> list[dict]:
        return _data.stars_mall_products(category)

    def stars_product_detail(self, product_code: str) -> dict | None:
        return _data.stars_product_detail(product_code)

    def stars_redeem(self, product_code: str, user_id: str,
                     idempotency_key: str) -> dict:
        return _data.stars_redeem(product_code, user_id=user_id,
                                  idempotency_key=idempotency_key)

    # --- Order Flow ---

    def delivery_addresses(self, user_id: str) -> list[dict]:
        return _data.delivery_addresses(user_id)

    def create_address(self, user_id: str, city: str, address: str,
                       address_detail: str, contact_name: str, phone: str) -> dict:
        return _data.create_address(city, address, address_detail,
                                    contact_name, phone, user_id=user_id)

    def store_coupons(self, store_id: str, user_id: str) -> list[dict]:
        return _data.store_coupons(store_id, user_id=user_id)

    def calculate_price(self, store_id: str, items: list[dict],
                        coupon_code: str | None = None) -> dict:
        return _data.calculate_price(store_id, items, coupon_code)

    def create_order(self, store_id: str, items: list[dict], pickup_type: str,
                     user_id: str, idempotency_key: str,
                     coupon_code: str | None = None,
                     address_id: str | None = None) -> dict:
        return _data.create_order(store_id, items, pickup_type,
                                  coupon_code=coupon_code,
                                  address_id=address_id,
                                  user_id=user_id,
                                  idempotency_key=idempotency_key)

    def order_status(self, order_id: str, user_id: str) -> dict | None:
        return _data.order_status(order_id, user_id=user_id)
