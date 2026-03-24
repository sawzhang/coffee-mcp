---
name: coffee-assets
description: 查询Coffee Company客户资产概览。当用户询问客户资产、资产总览、会员有什么券和权益等内容时使用。适用于"查一下客户资产"、"这个会员有哪些券"、"资产概览"等请求。
allowed-tools: mcp__coffee-mcp__assets_list
---

# 客户资产查询

调用 `assets_list` 查询会员的全部资产（优惠券 + 权益券），一览式展示。

参数：`member_id`（会员ID）

以清晰的列表展示所有资产，区分优惠券和权益券，标注每项的状态和有效期。
