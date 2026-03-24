---
name: coffee-member
description: 查询Coffee Company会员信息。当用户询问会员查询、会员等级、会员权益、手机号查会员、星星数等内容时使用。适用于"帮我查个会员"、"这个会员什么等级"、"查一下权益状态"等请求。
allowed-tools: mcp__coffee-mcp__member_query, mcp__coffee-mcp__member_tier, mcp__coffee-mcp__member_benefits, mcp__coffee-mcp__member_benefit_list
---

# 会员信息查询

查询 Coffee Company 会员的完整画像：基本信息、等级、权益状态、券列表。

## 查询策略

1. 如果用户提供了手机号/openId/memberId → 先调用 `member_query` 获取基本信息
2. 如果用户还想了解等级详情 → 调用 `member_tier`
3. 如果用户问权益状态 → 调用 `member_benefits`（8项权益清单）
4. 如果用户问有什么券 → 调用 `member_benefit_list`

## 参数说明

- `member_query`: 传 `mobile`（手机号）、`open_id`（第三方openId）或 `member_id`（会员ID），至少一个
- `member_tier` / `member_benefits` / `member_benefit_list`: 传 `member_id`

如果用户只给了手机号，先用 `member_query` 查到 memberId，再用于后续查询。

以友好的方式展示结果，重点突出等级、星星数、可用权益等关键信息。
