"""Brand category presets — sensible defaults per industry vertical.

Each preset provides complete menu options, validation rules, and feature flags
for a specific brand category. Brands only need to override what's different.

Usage:
    from coffee_mcp.presets.catalog import PRESETS, get_preset
    preset = get_preset("coffee")
    # Override specific values, generate brand.yaml
"""

PRESETS: dict[str, dict] = {
    "coffee": {
        "display_name": "咖啡",
        "description": "精品咖啡 / 连锁咖啡",
        "examples": "Manner, M Stand, Peet's, %Arabica, Seesaw",
        "size_options": {
            "tall":   {"name": "中杯",   "extra_price": 0},
            "grande": {"name": "大杯",   "extra_price": 4},
            "venti":  {"name": "超大杯", "extra_price": 7},
        },
        "milk_options": {
            "whole":   {"name": "全脂牛奶", "extra_price": 0},
            "skim":    {"name": "脱脂牛奶", "extra_price": 0},
            "oat":     {"name": "燕麦奶",   "extra_price": 5},
            "almond":  {"name": "杏仁奶",   "extra_price": 5},
            "soy":     {"name": "豆奶",     "extra_price": 4},
            "coconut": {"name": "椰奶",     "extra_price": 5},
        },
        "temp_options": {
            "hot":     {"name": "热"},
            "iced":    {"name": "冰"},
            "blended": {"name": "冰沙"},
        },
        "sweetness_options": {
            "normal": {"name": "标准糖"},
            "less":   {"name": "少糖"},
            "half":   {"name": "半糖"},
            "none":   {"name": "无糖"},
        },
        "extra_options": {
            "extra_shot":     {"name": "浓缩+1份",  "price": 6},
            "vanilla_syrup":  {"name": "香草糖浆",  "price": 4},
            "caramel_syrup":  {"name": "焦糖糖浆",  "price": 4},
            "hazelnut_syrup": {"name": "榛果糖浆",  "price": 4},
            "whipped_cream":  {"name": "奶油顶",    "price": 3},
            "cocoa_powder":   {"name": "可可粉",    "price": 0},
        },
        "validation": {
            "max_quantity": 99,
            "max_items_per_order": 20,
            "max_addresses": 10,
        },
        "features": {
            "campaigns": True,
            "coupons": True,
            "stars_mall": True,
            "delivery": True,
            "nutrition": True,
        },
        "rate_limits": {
            "L0": {"max_calls": 60, "window_seconds": 60},
            "L1": {"max_calls": 30, "window_seconds": 60},
            "L2": {"max_calls": 5,  "window_seconds": 3600},
            "L3": {"max_calls": 10, "window_seconds": 86400},
        },
    },
    "tea": {
        "display_name": "茶饮",
        "description": "新式茶饮 / 奶茶",
        "examples": "喜茶, 奈雪, 茶颜悦色, 沪上阿姨, 古茗, 书亦",
        "size_options": {
            "regular": {"name": "常规", "extra_price": 0},
            "large":   {"name": "大杯", "extra_price": 3},
        },
        "milk_options": {
            "whole":   {"name": "鲜奶",   "extra_price": 0},
            "oat":     {"name": "燕麦奶", "extra_price": 4},
            "coconut": {"name": "椰奶",   "extra_price": 4},
        },
        "temp_options": {
            "hot":  {"name": "热"},
            "iced": {"name": "冰"},
        },
        "sweetness_options": {
            "normal": {"name": "正常糖"},
            "seven":  {"name": "七分糖"},
            "half":   {"name": "半糖"},
            "three":  {"name": "三分糖"},
            "none":   {"name": "不加糖"},
        },
        "extra_options": {
            "boba":          {"name": "珍珠",   "price": 3},
            "coconut_jelly": {"name": "椰果",   "price": 3},
            "red_bean":      {"name": "红豆",   "price": 3},
            "pudding":       {"name": "布丁",   "price": 4},
            "taro":          {"name": "芋圆",   "price": 4},
            "grass_jelly":   {"name": "仙草",   "price": 3},
        },
        "validation": {
            "max_quantity": 50,
            "max_items_per_order": 15,
            "max_addresses": 5,
        },
        "features": {
            "campaigns": True,
            "coupons": True,
            "stars_mall": False,
            "delivery": True,
            "nutrition": True,
        },
        "rate_limits": {
            "L0": {"max_calls": 60, "window_seconds": 60},
            "L1": {"max_calls": 30, "window_seconds": 60},
            "L2": {"max_calls": 3,  "window_seconds": 3600},
            "L3": {"max_calls": 5,  "window_seconds": 86400},
        },
    },
    "juice": {
        "display_name": "果汁 / 鲜榨",
        "description": "鲜榨果汁 / 果昔 / 轻食",
        "examples": "茶百道(果茶), 满记, 鲜丰水果",
        "size_options": {
            "regular": {"name": "常规", "extra_price": 0},
            "large":   {"name": "大杯", "extra_price": 5},
        },
        "milk_options": {
            "none":    {"name": "无奶",   "extra_price": 0},
            "yogurt":  {"name": "酸奶",   "extra_price": 5},
            "coconut": {"name": "椰奶",   "extra_price": 4},
        },
        "temp_options": {
            "iced":    {"name": "冰"},
            "normal":  {"name": "常温"},
        },
        "sweetness_options": {
            "normal": {"name": "正常"},
            "less":   {"name": "少糖"},
            "none":   {"name": "不加糖"},
        },
        "extra_options": {
            "chia_seed":  {"name": "奇亚籽", "price": 3},
            "coconut":    {"name": "椰果",   "price": 3},
            "nata":       {"name": "寒天",   "price": 3},
        },
        "validation": {
            "max_quantity": 30,
            "max_items_per_order": 10,
            "max_addresses": 5,
        },
        "features": {
            "campaigns": True,
            "coupons": True,
            "stars_mall": False,
            "delivery": True,
            "nutrition": True,
        },
        "rate_limits": {
            "L0": {"max_calls": 60, "window_seconds": 60},
            "L1": {"max_calls": 30, "window_seconds": 60},
            "L2": {"max_calls": 3,  "window_seconds": 3600},
            "L3": {"max_calls": 5,  "window_seconds": 86400},
        },
    },
    "bakery": {
        "display_name": "烘焙 / 甜品",
        "description": "面包烘焙 / 蛋糕甜品",
        "examples": "奈雪(烘焙), 好利来, 鲍师傅, 泸溪河",
        "size_options": {
            "single": {"name": "单份", "extra_price": 0},
            "combo":  {"name": "套餐", "extra_price": 10},
        },
        "milk_options": {},
        "temp_options": {
            "normal":  {"name": "常温"},
            "warm":    {"name": "加热"},
        },
        "sweetness_options": {},
        "extra_options": {
            "gift_box":   {"name": "礼盒装", "price": 8},
            "extra_cream": {"name": "加奶油", "price": 5},
        },
        "validation": {
            "max_quantity": 50,
            "max_items_per_order": 20,
            "max_addresses": 5,
        },
        "features": {
            "campaigns": True,
            "coupons": True,
            "stars_mall": False,
            "delivery": True,
            "nutrition": False,
        },
        "rate_limits": {
            "L0": {"max_calls": 60, "window_seconds": 60},
            "L1": {"max_calls": 30, "window_seconds": 60},
            "L2": {"max_calls": 5,  "window_seconds": 3600},
            "L3": {"max_calls": 10, "window_seconds": 86400},
        },
    },
}


def get_preset(category: str) -> dict:
    """Get a preset by category name."""
    preset = PRESETS.get(category)
    if not preset:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown category '{category}'. Available: {available}")
    return preset


def list_presets() -> list[dict]:
    """List all available presets with metadata."""
    return [
        {
            "category": k,
            "display_name": v["display_name"],
            "description": v["description"],
            "examples": v["examples"],
        }
        for k, v in PRESETS.items()
    ]
