"""Brand adapter interface for ToC MCP platform.

Each brand implements this interface to connect MCP tools to its backend.
In demo mode, DemoAdapter returns mock data. In production, a brand
implements HTTP calls to its own API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BrandAdapter(ABC):
    """Abstract interface for brand backend integration.

    Method signatures map 1:1 to ToC MCP tools.
    """

    # --- Discovery ---
    @abstractmethod
    def campaign_calendar(self, month: str | None = None) -> list[dict]: ...

    @abstractmethod
    def available_coupons(self) -> list[dict]: ...

    @abstractmethod
    def claim_all_coupons(self, user_id: str) -> dict: ...

    # --- Account ---
    @abstractmethod
    def get_current_user(self, user_id: str) -> dict | None: ...

    @abstractmethod
    def my_account(self, user_id: str) -> dict | None: ...

    @abstractmethod
    def my_coupons(self, user_id: str, status: str | None = None) -> list[dict]: ...

    @abstractmethod
    def my_orders(self, user_id: str, limit: int = 10) -> list[dict]: ...

    # --- Menu ---
    @abstractmethod
    def nearby_stores(self, city: str | None = None, keyword: str | None = None) -> list[dict]: ...

    @abstractmethod
    def store_detail(self, store_id: str) -> dict | None: ...

    @abstractmethod
    def browse_menu(self, store_id: str) -> dict: ...

    @abstractmethod
    def drink_detail(self, product_code: str) -> dict | None: ...

    @abstractmethod
    def nutrition_info(self, product_code: str) -> dict | None: ...

    # --- Stars Mall ---
    @abstractmethod
    def stars_mall_products(self, category: str | None = None) -> list[dict]: ...

    @abstractmethod
    def stars_product_detail(self, product_code: str) -> dict | None: ...

    @abstractmethod
    def stars_redeem(self, product_code: str, user_id: str,
                     idempotency_key: str) -> dict: ...

    # --- Order Flow ---
    @abstractmethod
    def delivery_addresses(self, user_id: str) -> list[dict]: ...

    @abstractmethod
    def create_address(self, user_id: str, city: str, address: str,
                       address_detail: str, contact_name: str, phone: str) -> dict: ...

    @abstractmethod
    def store_coupons(self, store_id: str, user_id: str) -> list[dict]: ...

    @abstractmethod
    def calculate_price(self, store_id: str, items: list[dict],
                        coupon_code: str | None = None) -> dict: ...

    @abstractmethod
    def create_order(self, store_id: str, items: list[dict], pickup_type: str,
                     user_id: str, idempotency_key: str,
                     coupon_code: str | None = None,
                     address_id: str | None = None) -> dict: ...

    @abstractmethod
    def order_status(self, order_id: str, user_id: str) -> dict | None: ...
