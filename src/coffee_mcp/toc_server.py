"""Coffee Company ToC MCP Server — consumer-facing self-service tools.

21 tools covering the full consumer journey:
  Discovery → My Account → Menu → Stores → Points Mall → Order Flow

Auth: In production, user identity comes from Bearer token resolved at
connection time. In demo mode, uses default mock user CC_M_100001.

Security: Tools are classified into risk levels L0-L3. In production,
the gateway enforces per-level rate limiting and verification. See
docs/TOC_SECURITY.md for the full threat model.

Architecture:
  Consumer App → Gateway (auth + rate limit + bot detect)
    → toc_server.py → toc_mock_data.py → toc_formatters.py
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum

from mcp.server.fastmcp import FastMCP

from . import toc_mock_data as data
from . import toc_formatters as fmt


# =========================================================================
# Security: Tool risk levels + rate limiting
# =========================================================================

class RiskLevel(IntEnum):
    """Tool risk classification. See docs/TOC_SECURITY.md §3.1."""
    L0_PUBLIC_READ = 0   # Public info (menu, stores) — IP-level rate limit
    L1_AUTH_READ = 1     # User's own data — per-user rate limit
    L2_AUTH_WRITE = 2    # Writes with frequency control (claim coupons, add address)
    L3_HIGH_RISK = 3     # Transaction operations (redeem, order) — captcha + risk control


# Per-user rate limiter (in-memory, demo only; production uses Redis/gateway)
@dataclass
class _RateLimit:
    max_calls: int
    window_seconds: int
    calls: dict = field(default_factory=lambda: defaultdict(list))

    def check(self, user_id: str) -> bool:
        """Return True if request is allowed."""
        now = time.monotonic()
        user_calls = self.calls[user_id]
        # Evict expired entries
        self.calls[user_id] = [t for t in user_calls if now - t < self.window_seconds]
        if len(self.calls[user_id]) >= self.max_calls:
            return False
        self.calls[user_id].append(now)
        return True


# Rate limit configs per risk level
_RATE_LIMITS: dict[RiskLevel, _RateLimit] = {
    RiskLevel.L0_PUBLIC_READ: _RateLimit(max_calls=60, window_seconds=60),
    RiskLevel.L1_AUTH_READ:   _RateLimit(max_calls=30, window_seconds=60),
    RiskLevel.L2_AUTH_WRITE:  _RateLimit(max_calls=5,  window_seconds=3600),   # 5/hour
    RiskLevel.L3_HIGH_RISK:   _RateLimit(max_calls=10, window_seconds=86400),  # 10/day
}

# Tool → risk level mapping
_TOOL_RISK: dict[str, RiskLevel] = {
    # L0: Public read
    "now_time_info": RiskLevel.L0_PUBLIC_READ,
    "browse_menu": RiskLevel.L0_PUBLIC_READ,
    "drink_detail": RiskLevel.L0_PUBLIC_READ,
    "nutrition_info": RiskLevel.L0_PUBLIC_READ,
    "nearby_stores": RiskLevel.L0_PUBLIC_READ,
    "store_detail": RiskLevel.L0_PUBLIC_READ,
    # L1: Auth read
    "campaign_calendar": RiskLevel.L1_AUTH_READ,
    "available_coupons": RiskLevel.L1_AUTH_READ,
    "my_account": RiskLevel.L1_AUTH_READ,
    "my_coupons": RiskLevel.L1_AUTH_READ,
    "my_orders": RiskLevel.L1_AUTH_READ,
    "delivery_addresses": RiskLevel.L1_AUTH_READ,
    "stars_mall_products": RiskLevel.L1_AUTH_READ,
    "stars_product_detail": RiskLevel.L1_AUTH_READ,
    "store_coupons": RiskLevel.L1_AUTH_READ,
    "order_status": RiskLevel.L1_AUTH_READ,
    # L2: Auth write
    "claim_all_coupons": RiskLevel.L2_AUTH_WRITE,
    "create_address": RiskLevel.L2_AUTH_WRITE,
    # calculate_price is read-like (no state mutation), use L1 rate limit
    "calculate_price": RiskLevel.L1_AUTH_READ,
    # L3: High risk
    "stars_redeem": RiskLevel.L3_HIGH_RISK,
    "create_order": RiskLevel.L3_HIGH_RISK,
}


def _check_rate_limit(tool_name: str, user_id: str = data.DEFAULT_USER_ID) -> str | None:
    """Check rate limit for a tool. Returns error message if blocked, None if OK."""
    level = _TOOL_RISK.get(tool_name, RiskLevel.L1_AUTH_READ)
    limiter = _RATE_LIMITS.get(level)
    if limiter and not limiter.check(f"{user_id}:{tool_name}"):
        return "操作过于频繁，请稍后再试。"
    return None


# Input validators
_PHONE_RE = re.compile(r"^1\d{10}$")
_VALID_SIZES = {"tall", "grande", "venti"}
_VALID_MILKS = {"whole", "skim", "oat", "almond", "soy", "coconut"}
_VALID_TEMPS = {"hot", "iced", "blended"}
_VALID_EXTRAS = {"extra_shot", "vanilla_syrup", "caramel_syrup",
                 "hazelnut_syrup", "whipped_cream", "cocoa_powder"}
_VALID_PICKUP = {"自提", "外送", "堂食"}
_MAX_QUANTITY = 99
_MAX_ITEMS_PER_ORDER = 20
_MAX_ADDRESSES = 10


def _validate_cart_items(items: list[dict]) -> str | None:
    """Validate cart items. Returns error message or None."""
    if not items:
        return "商品列表不能为空。"
    if len(items) > _MAX_ITEMS_PER_ORDER:
        return f"单次最多 {_MAX_ITEMS_PER_ORDER} 件商品。"
    for i, item in enumerate(items):
        if "product_code" not in item:
            return f"第 {i+1} 件商品缺少 product_code。"
        qty = item.get("quantity", 1)
        if not isinstance(qty, int) or qty < 1 or qty > _MAX_QUANTITY:
            return f"商品数量须在 1-{_MAX_QUANTITY} 之间。"
        size = item.get("size")
        if size and size not in _VALID_SIZES:
            return f"杯型 '{size}' 无效，可选: {', '.join(sorted(_VALID_SIZES))}。"
        milk = item.get("milk")
        if milk and milk not in _VALID_MILKS:
            return f"奶类 '{milk}' 无效，可选: {', '.join(sorted(_VALID_MILKS))}。"
        for extra in item.get("extras", []):
            if extra not in _VALID_EXTRAS:
                return f"加料 '{extra}' 无效，可选: {', '.join(sorted(_VALID_EXTRAS))}。"
    return None


mcp = FastMCP(
    "Coffee Company ToC",
    instructions=(
        "Coffee Company 消费者自助 MCP Server。\n"
        "提供活动发现、优惠券领取、菜单浏览、门店查找、积分商城、下单点餐等能力。\n"
        "所有工具基于登录用户身份自动识别，无需传入会员ID。\n"
        "Demo 模式默认用户：张三（金星级，142颗星星）。\n\n"
        "安全说明：工具按风险分为 L0(公开只读) ~ L3(高危写入) 四级，\n"
        "高危操作有频率限制和参数校验，详见 docs/TOC_SECURITY.md。\n\n"
        "重要：下单前必须先调用 calculate_price 获取 confirmation_token，\n"
        "然后将 confirmation_token 传入 create_order。\n"
        "L3 操作（create_order, stars_redeem）需要 idempotency_key 防重复。"
    ),
)


# =========================================================================
# Group 0: Utility (1 tool)
# =========================================================================

@mcp.tool()
def now_time_info() -> str:
    """返回当前日期时间和星期，供判断活动有效期、门店营业时间等。[风险等级: L0]

    When:
    - 在查询活动日历、判断优惠券有效期之前调用
    - 判断门店是否在营业时间内
    - 任何需要当前时间信息的场景
    """
    return fmt.format_now_time_info()


# =========================================================================
# Group 1: Discovery + Promotions (3 tools)
# =========================================================================

@mcp.tool()
def campaign_calendar(month: str | None = None) -> str:
    """查询活动日历，发现当前和即将开始的优惠活动。

    When:
    - 用户问"有什么活动"、"最近有什么优惠"、"这个月有什么活动"
    Next:
    - 看到感兴趣的活动后，引导用户查看可领取的优惠券

    Args:
        month: 可选，查询指定月份 (格式: yyyy-MM)，默认当月
    """
    campaigns = data.campaign_calendar(month)
    return fmt.format_campaigns(campaigns)


@mcp.tool()
def available_coupons() -> str:
    """查询当前可领取的优惠券列表。类似"券中心"或"领券页"。

    When:
    - 用户问"有什么券可以领"、"可领的优惠券"、"券中心"
    Next:
    - 用户想全部领取时，引导使用 claim_all_coupons
    - 想了解具体券的使用范围，引导查看菜单
    """
    coupons = data.available_coupons()
    return fmt.format_available_coupons(coupons)


@mcp.tool()
def claim_all_coupons() -> str:
    """一键领取所有可领取的优惠券。[风险等级: L2]

    安全限制: 每用户每小时最多 5 次
    When:
    - 用户说"帮我领券"、"一键领取"、"全部领了"
    Next:
    - 领取成功后，引导用户查看 my_coupons 或去下单
    """
    if err := _check_rate_limit("claim_all_coupons"):
        return err
    result = data.claim_all_coupons()
    return fmt.format_claim_result(result)


# =========================================================================
# Group 2: My Account (3 tools)
# =========================================================================

@mcp.tool()
def my_account() -> str:
    """查询我的账户信息：等级、星星余额、可用权益、优惠券数量。

    When:
    - 用户问"我的等级"、"我有多少星星"、"我的账户"、"积分余额"
    Next:
    - 想看券详情 → my_coupons
    - 想用星星兑换 → stars_mall_products
    """
    info = data.my_account()
    if not info:
        return "未能获取账户信息，请确认登录状态。"
    return fmt.format_my_account(info)


@mcp.tool()
def my_coupons(status: str | None = None) -> str:
    """查询我已有的优惠券列表。

    When:
    - 用户问"我有什么券"、"我的优惠券"、"可用的券"
    Next:
    - 想用券下单 → 先选门店 nearby_stores，再看菜单 browse_menu

    Args:
        status: 可选筛选状态 "valid"(可用) / "used"(已使用)，默认全部
    """
    items = data.my_coupons(status=status)
    return fmt.format_my_coupons(items)


@mcp.tool()
def my_orders(limit: int = 5) -> str:
    """查询我的最近订单。

    When:
    - 用户问"我的订单"、"最近点了什么"、"订单记录"
    Next:
    - 想看具体订单 → order_status
    - 想再来一单 → nearby_stores 选门店

    Args:
        limit: 返回最近几笔订单，默认5
    """
    orders = data.my_orders(limit=limit)
    return fmt.format_my_orders(orders)


# =========================================================================
# Group 3: Menu + Drinks (3 tools)
# =========================================================================

@mcp.tool()
def browse_menu(store_id: str, compact: bool = False) -> str:
    """浏览门店菜单，查看饮品和食品列表。

    Preconditions:
    - 【强制】必须先调用 nearby_stores 获取门店信息，使用返回的 store_id
    When:
    - 用户说"看看菜单"、"有什么喝的"、"点个咖啡"
    Next:
    - 选中商品后 → drink_detail 查看自定义选项
    - 确定商品后 → calculate_price 计算价格

    Args:
        store_id: 门店ID，必须从 nearby_stores 返回结果获取
        compact: 紧凑模式，减少输出 token 消耗（默认 false）
    """
    menu = data.browse_menu(store_id)
    if compact:
        return fmt.format_menu_compact(menu)
    return fmt.format_menu(menu)


@mcp.tool()
def drink_detail(product_code: str) -> str:
    """查看单个饮品的详细信息和自定义选项（杯型/奶类/温度/甜度/加料）。

    When:
    - 用户说"这个饮品详情"、"拿铁有什么选项"、"能选什么奶"
    Next:
    - 确定定制后 → calculate_price 计算价格
    - 想看营养 → nutrition_info

    Args:
        product_code: 商品编号（如 D003），从 browse_menu 返回获取
    """
    item = data.drink_detail(product_code)
    if not item:
        return f"未找到商品 {product_code}。请检查商品编号。"
    return fmt.format_drink_detail(item)


@mcp.tool()
def nutrition_info(product_code: str, compact: bool = False) -> str:
    """查询饮品或食品的营养成分信息（热量、蛋白质、脂肪等）。

    When:
    - 用户问"这个多少卡"、"热量是多少"、"营养信息"
    - 帮用户搭配低卡套餐时

    Args:
        product_code: 商品编号（如 D003）
        compact: 紧凑模式，单行输出营养数据（默认 false）
    """
    info = data.nutrition_info(product_code)
    if not info:
        return f"未找到商品 {product_code} 的营养信息。"
    if compact:
        return fmt.format_nutrition_compact(info)
    return fmt.format_nutrition(info)


# =========================================================================
# Group 4: Stores (2 tools)
# =========================================================================

@mcp.tool()
def nearby_stores(city: str | None = None, keyword: str | None = None) -> str:
    """搜索附近门店，按城市或关键词筛选。

    When:
    - 用户说"附近有什么店"、"上海的门店"、"找一家店"
    Next:
    - 选中门店后 → browse_menu 查看菜单
    - 想了解门店详情 → store_detail
    - 想看门店可用券 → store_coupons

    Args:
        city: 可选，城市名（如 "上海"）
        keyword: 可选，关键词搜索（如 "南京西路"）
    """
    stores = data.nearby_stores(city=city, keyword=keyword)
    return fmt.format_nearby_stores(stores)


@mcp.tool()
def store_detail(store_id: str) -> str:
    """查看门店详细信息：地址、营业时间、服务、特色。

    Args:
        store_id: 门店ID，从 nearby_stores 返回获取
    """
    store = data.store_detail(store_id)
    if not store:
        return f"未找到门店 {store_id}。"
    return fmt.format_store_detail(store)


# =========================================================================
# Group 5: Points Mall (3 tools)
# =========================================================================

@mcp.tool()
def stars_mall_products(category: str | None = None) -> str:
    """浏览积分商城，查看可用星星兑换的商品。

    When:
    - 用户问"积分能换什么"、"星星商城"、"可以兑换什么"
    Next:
    - 选中商品 → stars_product_detail 查看详情
    - 确认兑换 → stars_redeem

    Args:
        category: 可选，商品分类筛选（如 "饮品券"、"周边"、"权益卡"）
    """
    products = data.stars_mall_products(category)
    user = data.get_current_user()
    user_stars = user["star_balance"] if user else 0
    return fmt.format_stars_mall(products, user_stars)


@mcp.tool()
def stars_product_detail(product_code: str) -> str:
    """查看积分商城单个商品详情。

    Args:
        product_code: 积分商品编号（如 SM_001），从 stars_mall_products 获取
    """
    product = data.stars_product_detail(product_code)
    if not product:
        return f"未找到积分商品 {product_code}。"
    user = data.get_current_user()
    user_stars = user["star_balance"] if user else 0
    return fmt.format_stars_product_detail(product, user_stars)


@mcp.tool()
def stars_redeem(product_code: str, idempotency_key: str) -> str:
    """用星星兑换积分商城商品。[风险等级: L3]

    安全限制: 每用户每天最多 10 次，生产环境需人机验证
    Preconditions:
    - 必须先查看 stars_product_detail 确认商品信息
    - 用户确认兑换后才可调用
    When:
    - 用户说"兑换这个"、"用星星换"、"确认兑换"
    On Error:
    - 星星不足时提示差额
    - 库存不足时提示

    Args:
        product_code: 积分商品编号（如 SM_001）
        idempotency_key: 幂等键，防止重复兑换（由客户端生成的唯一标识）
    """
    if err := _check_rate_limit("stars_redeem"):
        return err
    result = data.stars_redeem(product_code, idempotency_key=idempotency_key)
    return fmt.format_stars_redeem_result(result)


# =========================================================================
# Group 6: Order Flow (6 tools)
# =========================================================================

@mcp.tool()
def delivery_addresses() -> str:
    """查询我的配送地址列表。

    When:
    - 用户选择外送时，需要先查看/选择配送地址
    Next:
    - 没有地址 → create_address 添加新地址
    - 有地址 → 选择地址后继续下单 create_order
    """
    addrs = data.delivery_addresses()
    return fmt.format_delivery_addresses(addrs)


@mcp.tool()
def create_address(city: str, address: str, address_detail: str,
                   contact_name: str, phone: str) -> str:
    """创建新的配送地址。

    Preconditions:
    - 必须提供完整的地址信息，不可使用示例值
    - 如果用户未提供必填信息，必须先询问
    When:
    - 用户说"添加地址"、"新建配送地址"
    Next:
    - 创建成功后继续下单流程

    Args:
        city: 城市（如 "上海"）
        address: 详细地址（如 "南京西路1515号静安嘉里中心"）
        address_detail: 门牌号（如 "2号楼15F"）
        contact_name: 联系人姓名
        phone: 手机号（11位）
    """
    if err := _check_rate_limit("create_address"):
        return err
    # Validate phone format
    if not _PHONE_RE.match(phone):
        return "手机号格式无效，请输入11位手机号。"
    # Check address count limit
    existing = data.delivery_addresses()
    if len(existing) >= _MAX_ADDRESSES:
        return f"最多保存 {_MAX_ADDRESSES} 个地址，请先删除不用的地址。"
    # Validate required fields not empty
    if not all([city.strip(), address.strip(), address_detail.strip(),
                contact_name.strip()]):
        return "地址信息不完整，请填写所有必填项。"
    addr = data.create_address(city, address, address_detail, contact_name, phone)
    return fmt.format_new_address(addr)


@mcp.tool()
def store_coupons(store_id: str) -> str:
    """查询在指定门店可使用的优惠券。

    Preconditions:
    - 【强制】必须先调用 nearby_stores 获取门店信息
    When:
    - 用户问"这个店能用什么券"、"有可用的优惠吗"
    Next:
    - 选择券后 → calculate_price 计算使用券后的价格

    Args:
        store_id: 门店ID，从 nearby_stores 返回获取
    """
    store = data.store_detail(store_id)
    store_name = store["name"] if store else store_id
    coupons = data.store_coupons(store_id)
    return fmt.format_store_coupons(coupons, store_name)


@mcp.tool()
def calculate_price(store_id: str, items: list[dict],
                    coupon_code: str | None = None) -> str:
    """计算订单价格（含优惠），返回确认令牌用于下单。

    Preconditions:
    - 【强制】必须先调用 nearby_stores 获取门店 store_id
    - 商品 product_code 必须从 browse_menu 查询获取
    When:
    - 用户问"多少钱"、"算一下价格"、"加上券多少"
    Next:
    - 用户确认价格后 → 将返回的 confirmation_token 传入 create_order

    Args:
        store_id: 门店ID
        items: 商品列表，每项包含:
          - product_code: 商品编号 (必填)
          - quantity: 数量 (默认1)
          - size: 杯型 "tall"/"grande"/"venti" (可选)
          - milk: 奶类 "whole"/"oat"/"almond"/"soy"/"coconut" (可选)
          - extras: 加料列表如 ["extra_shot","vanilla_syrup"] (可选)
        coupon_code: 优惠券ID（可选，从 store_coupons 或 my_coupons 获取）
    """
    if err := _validate_cart_items(items):
        return err
    result = data.calculate_price(store_id, items, coupon_code)
    return fmt.format_price_calculation(result)


@mcp.tool()
def create_order(store_id: str, items: list[dict], pickup_type: str,
                 idempotency_key: str,
                 confirmation_token: str,
                 coupon_code: str | None = None,
                 address_id: str | None = None) -> str:
    """创建订单。[风险等级: L3]

    Preconditions:
    - 【强制】下单前必须先调用 calculate_price 获取 confirmation_token
    - 【强制】必须等待用户确认价格后才可调用
    - 【强制】必须已调用 nearby_stores 获取门店信息
    - 外送订单必须提供 address_id（从 delivery_addresses 获取）
    When:
    - 用户说"下单"、"我要点这个"、"确认订单"
    Next:
    - 下单成功后引导用户完成支付
    - 支付后说"支付完成"查询 order_status
    On Error:
    - 门店不营业时提示
    - 商品不存在时提示

    Args:
        store_id: 门店ID
        items: 商品列表（同 calculate_price 格式）
        pickup_type: 取餐方式 "自提" / "外送" / "堂食"
        idempotency_key: 幂等键，防止重复下单（由客户端生成的唯一标识）
        confirmation_token: 确认令牌（从 calculate_price 返回获取，有效期5分钟）
        coupon_code: 优惠券ID（可选）
        address_id: 配送地址ID（外送时必填，从 delivery_addresses 获取）
    """
    if err := _check_rate_limit("create_order"):
        return err
    if err := _validate_cart_items(items):
        return err
    if pickup_type not in _VALID_PICKUP:
        return f"取餐方式 '{pickup_type}' 无效，可选: {', '.join(sorted(_VALID_PICKUP))}。"
    if pickup_type == "外送" and not address_id:
        return "外送订单必须提供配送地址ID。请先调用 delivery_addresses 获取。"
    # Validate confirmation token
    token_err = data.validate_confirmation_token(confirmation_token)
    if token_err:
        return token_err
    result = data.create_order(store_id, items, pickup_type,
                               coupon_code=coupon_code, address_id=address_id,
                               idempotency_key=idempotency_key)
    return fmt.format_order_created(result)


@mcp.tool()
def order_status(order_id: str) -> str:
    """查询订单状态详情。

    When:
    - 用户说"查下订单"、"支付完成"、"订单什么状态了"

    Args:
        order_id: 订单号（从 create_order 或 my_orders 获取）
    """
    order = data.order_status(order_id)
    if not order:
        return f"未找到订单 {order_id}。请检查订单号。"
    return fmt.format_order_status(order)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
