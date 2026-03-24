---
name: coffee-coupons
description: 查询Coffee Company券码信息。当用户询问券码状态、券码详情、订单券码、优惠券查询等内容时使用。适用于"这张券什么状态"、"查一下这个券码"、"订单出券了吗"等请求。
allowed-tools: mcp__coffee-mcp__coupon_query, mcp__coffee-mcp__coupon_detail
---

# 券码查询

查询 Coffee Company 券码状态和详情。

## 工具选择

| 场景 | 工具 | 参数 |
|------|------|------|
| 查订单关联的券码生成状态 | `coupon_query` | `order_id` (订单号) |
| 查单张券码详细信息 | `coupon_detail` | `coupon_code` (券码) |

## 券码状态说明

- 4 = 未使用
- 10 = 已使用
- 20 = 已过期
- 30 = 已作废

展示时重点显示：券码、状态、面值、有效期、核销次数。
