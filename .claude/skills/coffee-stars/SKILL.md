---
name: coffee-stars
description: Coffee Company积分商城和星星兑换。当用户询问积分兑换、星星商城、能换什么、积分余额等内容时使用。适用于"我的星星够换什么"、"积分商城"、"用星星兑换"等请求。
allowed-tools: mcp__coffee-toc__my_account, mcp__coffee-toc__stars_mall_products, mcp__coffee-toc__stars_product_detail, mcp__coffee-toc__stars_redeem
---

# 积分商城

帮助用户浏览积分商城和使用星星兑换商品。

## 兑换流程

1. `my_account` → 查看星星余额
2. `stars_mall_products` → 浏览可兑商品
3. `stars_product_detail` → 查看商品详情
4. `stars_redeem` → 确认兑换（需用户确认后才可调用）

兑换成功后券会自动放入卡包。
