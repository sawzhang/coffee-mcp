"""Shared utilities for Coffee Company MCP platform."""

import uuid


def random_id(prefix: str) -> str:
    """Generate a randomized ID like 'ord_a7f3b2e9' to prevent enumeration."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def mask_phone(phone: str) -> str:
    """Mask phone number for list views: 13812341234 → 138****1234"""
    if len(phone) == 11:
        return f"{phone[:3]}****{phone[7:]}"
    return phone
