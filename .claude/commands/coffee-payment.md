# 支付状态查询

调用 `cashier_pay_query` 查询收银台支付结果。

参数：`pay_token`（支付令牌）

支付状态: 0=支付中, 1=支付成功, 2=支付失败

展示支付结果，如果失败或处理中，给出建议。

## Demo 数据

- PAY_TOKEN_001 (成功), PAY_TOKEN_002 (处理中), PAY_TOKEN_003 (失败)

$ARGUMENTS
