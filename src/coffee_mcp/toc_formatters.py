"""Semantic formatters for Coffee Company ToC (consumer-facing) MCP Server.

Transforms backend response dicts into natural language markdown for LLM consumption.
Consumer-facing tone: friendly, concise, action-oriented.

Supports standard and compact output modes to optimize token consumption.
PII masking applied in list views (phone numbers masked as 138****1234).
"""

from datetime import datetime

from . import toc_mock_data as tmd


# ---------------------------------------------------------------------------
# Utility: now_time_info
# ---------------------------------------------------------------------------

def format_now_time_info() -> str:
    """Format current date/time for LLM context."""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return (
        f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        f"（{weekdays[now.weekday()]}）"
    )


# ---------------------------------------------------------------------------
# My Account
# ---------------------------------------------------------------------------

def format_my_account(data: dict) -> str:
    t = data["tier_info"]
    lines = [
        f"**我的账户**\n",
        f"- 昵称：{data['name']}",
        f"- 等级：{t['tier_name']}（{t['member_tier']}）",
        f"- 星星：{t['star_balance']} 颗",
    ]
    if t.get("next_tier"):
        lines.append(f"- 距 {t['next_tier_name']} 还差 {t['stars_to_next']} 颗星")
    else:
        lines.append("- 已达最高等级")
    lines.append(f"- 等级有效期至 {t['tier_expire_date']}")
    lines.append(f"- 可用权益 {data['active_benefits']} 项 | 优惠券 {data['coupon_count']} 张")
    return "\n".join(lines)


def format_my_coupons(items: list[dict]) -> str:
    if not items:
        return "你目前没有优惠券。去「可领取优惠券」看看有没有新券吧！"
    valid = [i for i in items if i["status"] in ("未使用", "可使用")]
    lines = [f"**我的优惠券**（共 {len(items)} 张，{len(valid)} 张可用）\n"]
    for c in items:
        icon = "🟢" if c["status"] in ("未使用", "可使用") else "⬜"
        value = f"¥{c['face_value']:.0f}" if c.get("face_value") else "无面值"
        lines.append(f"- {icon} **{c['name']}**（{c['type']}）| {c['status']} | 至 {c['valid_end']} | {value}")
    return "\n".join(lines)


def format_my_orders(orders: list[dict]) -> str:
    if not orders:
        return "你还没有订单。去点一杯吧！"
    lines = [f"**我的订单**（最近 {len(orders)} 笔）\n"]
    for o in orders:
        icon = {"已完成": "✅", "制作中": "☕", "待支付": "⏳", "配送中": "🚗",
                "已取消": "❌"}.get(o["status"], "📋")
        item_names = "、".join(f"{i['name']}" for i in o["items"])
        lines.append(
            f"- {icon} **{o['order_id']}** | {o['status']}\n"
            f"  {item_names} | ¥{o['final_price']:.0f} | {o['pickup_type']}\n"
            f"  {o['store_name']} | {o['order_time']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Campaigns + Coupons
# ---------------------------------------------------------------------------

def format_campaigns(campaigns: list[dict]) -> str:
    if not campaigns:
        return "本月暂无活动，敬请期待！"
    active = [c for c in campaigns if c["status"] == "进行中"]
    upcoming = [c for c in campaigns if c["status"] == "未开始"]
    ended = [c for c in campaigns if c["status"] == "已结束"]

    lines = [f"**活动日历**（共 {len(campaigns)} 个活动）\n"]

    if active:
        lines.append("**进行中：**")
        for c in active:
            tags = " ".join(f"[{t}]" for t in c.get("tags", []))
            lines.append(f"- **{c['title']}** {tags}\n  {c['description']}\n  {c['start_date']} ~ {c['end_date']}")
    if upcoming:
        lines.append("\n**即将开始：**")
        for c in upcoming:
            tags = " ".join(f"[{t}]" for t in c.get("tags", []))
            lines.append(f"- **{c['title']}** {tags}\n  {c['description']}\n  {c['start_date']} ~ {c['end_date']}")
    if ended:
        lines.append(f"\n另有 {len(ended)} 个已结束活动。")

    return "\n".join(lines)


def format_available_coupons(coupons: list[dict]) -> str:
    if not coupons:
        return "目前没有可领取的优惠券。"
    claimable = [c for c in coupons if c["status"] == "可领取"]
    lines = [f"**可领取优惠券**（{len(claimable)} 张可领 / 共 {len(coupons)} 张）\n"]
    for c in coupons:
        icon = "🎫" if c["status"] == "可领取" else "✅"
        val = f"减¥{c['discount_value']:.0f}" if c.get("discount_value") else "折扣券"
        lines.append(f"- {icon} **{c['name']}** | {val} | {c['status']}\n  {c['description']} | 领取后 {c['valid_days']} 天有效")
    if claimable:
        lines.append(f"\n说「帮我全部领取」可一键领取所有可领券！")
    return "\n".join(lines)


def format_claim_result(result: dict) -> str:
    if result["claimed_count"] == 0:
        return "没有新的可领取优惠券了。所有券都已领取！"
    names = "、".join(c["name"] for c in result["claimed_coupons"])
    return (
        f"**一键领券成功！**\n\n"
        f"- 本次领取：{result['claimed_count']} 张\n"
        f"- 已领取：{names}\n"
        f"- 之前已领：{result['already_claimed']} 张\n\n"
        f"券已放入你的卡包，下单时可使用。"
    )


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------

def format_nearby_stores(stores: list[dict]) -> str:
    if not stores:
        return "附近没有找到门店。试试其他地区？"
    lines = [f"**附近门店**（共 {len(stores)} 家）\n"]
    for s in stores:
        icon = "🟢" if s["status"] == "营业中" else "🔴"
        services = " / ".join(s["services"])
        features = "、".join(s["features"])
        lines.append(
            f"- {icon} **{s['name']}** [{s['status']}]\n"
            f"  {s['address']}\n"
            f"  {s['hours']} | {services}\n"
            f"  {features} | 门店ID: `{s['store_id']}`"
        )
    return "\n".join(lines)


def format_store_detail(store: dict) -> str:
    icon = "🟢" if store["status"] == "营业中" else "🔴"
    services = " / ".join(store["services"])
    features = "、".join(store["features"])
    return (
        f"**{store['name']}** {icon} {store['status']}\n\n"
        f"- 地址：{store['city']}{store['district']}{store['address']}\n"
        f"- 营业时间：{store['hours']}\n"
        f"- 电话：{store['phone']}\n"
        f"- 服务：{services}\n"
        f"- 特色：{features}\n"
        f"- 门店ID：`{store['store_id']}`"
    )


# ---------------------------------------------------------------------------
# Menu — standard + compact modes
# ---------------------------------------------------------------------------

def format_menu(data: dict) -> str:
    if "error" in data:
        return data["error"]
    lines = [f"**{data['store_name']} 菜单**\n"]
    for cat in data["categories"]:
        cat_items = [i for i in data["items"] if i["category"] == cat["code"]]
        if not cat_items:
            continue
        lines.append(f"\n**{cat['name']}**")
        for item in cat_items:
            new_tag = " 🆕" if item.get("is_new") else ""
            sizes = "/".join(
                tmd.SIZE_OPTIONS[s]["name"]
                for s in item.get("available_sizes", [])
            ) or "单一规格"
            lines.append(
                f"- **{item['name']}**{new_tag} | ¥{item['base_price']}起 | {sizes}\n"
                f"  {item['description']} | +{item['stars_earn']}星 | `{item['product_code']}`"
            )
    lines.append(f"\n说出商品编号（如 `D003`）查看详情和自定义选项。")
    return "\n".join(lines)


def format_menu_compact(data: dict) -> str:
    """Compact menu format — minimizes token consumption."""
    if "error" in data:
        return data["error"]
    lines = [f"**{data['store_name']} 菜单**\n"]
    lines.append("商品|价格|杯型|编号")
    lines.append("---|---|---|---")
    for item in data["items"]:
        new_tag = "🆕" if item.get("is_new") else ""
        sizes = "/".join(
            tmd.SIZE_OPTIONS[s]["name"]
            for s in item.get("available_sizes", [])
        ) or "单一"
        lines.append(f"{item['name']}{new_tag}|¥{item['base_price']}起|{sizes}|`{item['product_code']}`")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drink Detail
# ---------------------------------------------------------------------------

def format_drink_detail(item: dict) -> str:
    lines = [
        f"**{item['name']}**\n",
        f"{item['description']}\n",
        f"- 基础价格：¥{item['base_price']}",
        f"- 可赚星星：+{item['stars_earn']}颗",
        f"- 热量（中杯）：约 {item.get('calories_tall', '?')} kcal",
    ]
    if item.get("customizable"):
        if item.get("size_options"):
            size_str = " / ".join(
                f"{v['name']}(+¥{v['extra_price']})" if v["extra_price"] else v["name"]
                for v in item["size_options"].values()
            )
            lines.append(f"\n**杯型：** {size_str}")
        if item.get("temp_options"):
            temp_str = " / ".join(v["name"] for v in item["temp_options"].values())
            lines.append(f"**温度：** {temp_str}")
        if item.get("milk_options"):
            milk_str = " / ".join(
                f"{v['name']}(+¥{v['extra_price']})" if v["extra_price"] else v["name"]
                for v in item["milk_options"].values()
            )
            lines.append(f"**奶类：** {milk_str}")
        lines.append(f"**甜度：** " + " / ".join(
            v["name"] for v in item.get("sweetness_options", {}).values()
        ))
        if item.get("extra_options"):
            extra_str = " / ".join(
                f"{v['name']}(+¥{v['price']})" if v["price"] else v["name"]
                for v in item["extra_options"].values()
            )
            lines.append(f"**加料：** {extra_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Nutrition — standard + compact modes
# ---------------------------------------------------------------------------

def format_nutrition(data: dict) -> str:
    return (
        f"**{data['name']} 营养信息**（{data['serving']}）\n\n"
        f"| 营养成分 | 含量 |\n"
        f"|---------|------|\n"
        f"| 热量 | {data['calories']} kcal |\n"
        f"| 蛋白质 | {data['protein']}g |\n"
        f"| 脂肪 | {data['fat']}g |\n"
        f"| 碳水化合物 | {data['carbs']}g |\n"
        f"| 糖 | {data['sugar']}g |\n"
        f"| 钠 | {data['sodium']:.0f}mg |\n"
        f"| 咖啡因 | {data['caffeine']}mg |"
    )


def format_nutrition_compact(data: dict) -> str:
    """Compact nutrition format — single line, minimizes tokens."""
    return (
        f"{data['name']}({data['serving']}): "
        f"{data['calories']}kcal | "
        f"蛋白{data['protein']}g | "
        f"脂肪{data['fat']}g | "
        f"碳水{data['carbs']}g | "
        f"糖{data['sugar']}g | "
        f"钠{data['sodium']:.0f}mg | "
        f"咖啡因{data['caffeine']}mg"
    )


# ---------------------------------------------------------------------------
# Stars Mall
# ---------------------------------------------------------------------------

def format_stars_mall(products: list[dict], user_stars: int = 0) -> str:
    if not products:
        return "积分商城暂无商品。"
    lines = [f"**积分商城**（你有 {user_stars} 颗星星）\n"]
    for p in products:
        affordable = "✅" if user_stars >= p["stars_cost"] else "🔒"
        lines.append(
            f"- {affordable} **{p['name']}** | {p['stars_cost']}星\n"
            f"  {p['description']} | 库存{p['stock']} | `{p['product_code']}`"
        )
    return "\n".join(lines)


def format_stars_product_detail(product: dict, user_stars: int = 0) -> str:
    affordable = user_stars >= product["stars_cost"]
    status = f"可兑换（你有 {user_stars} 颗星）" if affordable else f"星星不足（需 {product['stars_cost']}，你有 {user_stars}）"
    return (
        f"**{product['name']}**\n\n"
        f"- 所需星星：{product['stars_cost']} 颗\n"
        f"- 分类：{product['category']}\n"
        f"- 描述：{product['description']}\n"
        f"- 库存：{product['stock']}\n"
        f"- 状态：{status}\n"
        f"- 商品编号：`{product['product_code']}`"
    )


def format_stars_redeem_result(result: dict) -> str:
    if not result["success"]:
        return f"兑换失败：{result['message']}"
    return (
        f"**兑换成功！**\n\n"
        f"- 兑换单号：`{result.get('redeem_id', '')}`\n"
        f"- 商品：{result['product_name']}\n"
        f"- 消耗星星：{result['stars_cost']} 颗\n"
        f"- 剩余星星：{result['stars_remaining']} 颗\n\n"
        f"券已发放到你的卡包，可在下单时使用。"
    )


# ---------------------------------------------------------------------------
# Price Calculation (with confirmation_token)
# ---------------------------------------------------------------------------

def format_price_calculation(data: dict) -> str:
    if "error" in data:
        return f"计算失败：{data['error']}"
    lines = ["**价格计算**\n"]
    for item in data["items"]:
        lines.append(f"- {item['name']}（{item.get('size', '')}）x{item['quantity']} = ¥{item['line_total']:.0f}")
    lines.append(f"\n- 商品总价：¥{data['original_price']:.0f}")
    if data["discount"] > 0:
        lines.append(f"- 优惠减免：-¥{data['discount']:.0f}（{data.get('coupon_name', '优惠券')}）")
    if data.get("delivery_fee"):
        lines.append(f"- 配送费：¥{data['delivery_fee']:.0f}")
    if data.get("packing_fee"):
        lines.append(f"- 打包费：¥{data['packing_fee']:.0f}")
    lines.append(f"- **应付：¥{data['final_price']:.0f}**")
    # Include confirmation token
    if data.get("confirmation_token"):
        lines.append(f"\n确认令牌：`{data['confirmation_token']}`")
        lines.append(f"（有效期5分钟，请确认后使用此令牌下单）")
    lines.append(f"\n确认后说「下单」即可创建订单。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

def format_order_created(data: dict) -> str:
    if "error" in data:
        return f"下单失败：{data['error']}"
    lines = [
        f"**订单已创建！**\n",
        f"- 订单号：`{data['order_id']}`",
        f"- 门店：{data['store_name']}",
        f"- 取餐方式：{data['pickup_type']}",
    ]
    if data.get("delivery_address"):
        lines.append(f"- 配送至：{data['delivery_address']}")
    for item in data["items"]:
        lines.append(f"- {item['name']}（{item.get('size', '')}）x{item['quantity']} = ¥{item['line_total']:.0f}")
    if data["discount"] > 0:
        lines.append(f"- 优惠：-¥{data['discount']:.0f}")
    lines.append(f"- **应付：¥{data['final_price']:.0f}**")
    lines.append(f"- 可赚星星：+{data.get('stars_will_earn', 0)}颗")
    lines.append(f"\n{data.get('message', '')}")
    lines.append(f"支付链接：{data.get('pay_url', '')}")
    lines.append(f"\n支付完成后回复「支付完成」查询最新状态。")
    return "\n".join(lines)


def format_order_status(order: dict) -> str:
    icon = {"已完成": "✅", "制作中": "☕", "待支付": "⏳", "配送中": "🚗",
            "待自提": "📦", "已取消": "❌", "已退款": "💰"}.get(order["status"], "📋")
    lines = [
        f"**订单详情** {icon}\n",
        f"- 订单号：`{order['order_id']}`",
        f"- 状态：**{order['status']}**",
        f"- 门店：{order['store_name']}",
        f"- 取餐方式：{order['pickup_type']}",
    ]
    if order.get("delivery_address"):
        lines.append(f"- 配送至：{order['delivery_address']}")
    for item in order["items"]:
        extras = ""
        if item.get("size"):
            extras += f"/{item['size']}"
        if item.get("milk"):
            extras += f"/{item['milk']}"
        if item.get("temp"):
            extras += f"/{item['temp']}"
        lines.append(f"- {item['name']}{extras} x{item['quantity']} = ¥{item['price']:.0f}")
    lines.append(f"- 实付：¥{order['final_price']:.0f}")
    if order.get("stars_earned"):
        lines.append(f"- 获得星星：+{order['stars_earned']}颗")
    lines.append(f"- 下单时间：{order['order_time']}")
    if order.get("complete_time"):
        lines.append(f"- 完成时间：{order['complete_time']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delivery Addresses (with PII masking)
# ---------------------------------------------------------------------------

def format_delivery_addresses(addresses: list[dict]) -> str:
    if not addresses:
        return "你还没有配送地址。说「添加地址」来创建一个吧！"
    lines = [f"**我的配送地址**（共 {len(addresses)} 个）\n"]
    for a in addresses:
        default = " [默认]" if a.get("is_default") else ""
        masked_phone = tmd.mask_phone(a["phone"])
        lines.append(
            f"- **{a['contact_name']}** {masked_phone}{default}\n"
            f"  {a['city']} {a['address']} {a['address_detail']}\n"
            f"  地址ID: `{a['address_id']}`"
        )
    return "\n".join(lines)


def format_new_address(addr: dict) -> str:
    return (
        f"**地址创建成功！**\n\n"
        f"- 联系人：{addr['contact_name']} {addr['phone']}\n"
        f"- 地址：{addr['city']} {addr['address']} {addr['address_detail']}\n"
        f"- 地址ID：`{addr['address_id']}`\n"
        f"- 默认地址：{'是' if addr.get('is_default') else '否'}"
    )


def format_store_coupons(coupons: list[dict], store_name: str = "") -> str:
    if not coupons:
        return f"你在{store_name}暂无可用优惠券。"
    lines = [f"**{store_name}可用优惠券**（共 {len(coupons)} 张）\n"]
    for c in coupons:
        value = f"¥{c['face_value']:.0f}" if c.get("face_value") else "无面值"
        lines.append(f"- **{c['name']}**（{c['type']}）| {value} | 至 {c['valid_end']}")
    lines.append(f"\n下单时可选择使用以上优惠券。")
    return "\n".join(lines)
