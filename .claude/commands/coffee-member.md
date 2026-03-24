# 会员信息查询

查询 Coffee Company 会员信息。

## 查询流程

1. 调用 `member_query` 获取会员基本信息（手机号/openId/memberId）
2. 获取 memberId 后，自动调用 `member_tier` 查询等级详情
3. 调用 `member_benefits` 展示权益状态

以友好方式展示：会员姓名、等级、星星数、距下一级差距、可用权益。

## Demo 数据

- CC_M_100001 (金星), CC_M_100002 (银星), CC_M_100003 (钻星)
- 手机号: 138****1234

$ARGUMENTS
