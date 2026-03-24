---
name: coffee-payment
description: 查询Coffee Company支付状态。当用户询问支付结果、付款状态、支付令牌查询等内容时使用。适用于"支付成功了吗"、"查一下支付状态"、"这笔付款什么情况"等请求。
allowed-tools: mcp__coffee-mcp__cashier_pay_query
---

# 支付状态查询

调用 `cashier_pay_query` 查询收银台支付结果。

参数：`pay_token`（支付令牌，收银下单接口返回的 payToken）

## 支付状态说明

- 0 = 支付中
- 1 = 支付成功
- 2 = 支付失败

展示时明确告知支付结果，如果失败或处理中，给出建议下一步操作。
