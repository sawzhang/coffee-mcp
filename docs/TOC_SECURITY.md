# Coffee Company ToC MCP — 安全架构设计

## 0. 核心矛盾

```
ToB: 千问/蔚来 → Kong (HMAC + IP白名单 + ACL) → MCP Adapter
     ↑ 可信对端，企业级鉴权，固定IP段，每年审计一次

ToC: 任意用户 → ??? → MCP Server → 后端
     ↑ 不可信对端，无固定IP，黄牛/脚本/爬虫随时来
```

**ToB 的安全假设（对端可信）在 ToC 场景下完全不成立。**

---

## 1. 威胁模型

### 1.1 黄牛风险（最大威胁）

| 攻击场景 | 对应工具 | 风险等级 | 影响 |
|---------|---------|---------|------|
| 批量领券 | `claim_all_coupons` | **极高** | 秒杀抢券，正常用户无券可领 |
| 批量注册薅券 | `claim_all_coupons` | **极高** | 批号注册 → 领券 → 转卖 |
| 刷积分兑换 | `stars_redeem` | **高** | 低价收积分号 → 兑换高价商品转卖 |
| 抢限量商品 | `create_order` (季节限定) | **高** | 脚本抢购限量品 |
| 刷优惠券下单 | `create_order` + 券 | **高** | 同一账号多设备并发用券 |

### 1.2 数据安全风险

| 攻击场景 | 对应工具 | 风险等级 | 影响 |
|---------|---------|---------|------|
| 遍历他人订单 | `order_status` | **高** | 订单号可猜测/枚举 |
| 遍历他人地址 | `delivery_addresses` | **高** | 地址ID可猜测 |
| 遍历门店信息 | `nearby_stores` | 低 | 门店信息本身是公开的 |
| 菜单/价格爬取 | `browse_menu` / `calculate_price` | 中 | 竞品情报收集 |

### 1.3 滥用风险

| 攻击场景 | 对应工具 | 风险等级 | 影响 |
|---------|---------|---------|------|
| 高频调用刷接口 | 全部 | **高** | 后端压力，服务降级 |
| 恶意创建大量地址 | `create_address` | 中 | 数据污染 |
| 恶意下单不付款 | `create_order` | 中 | 库存锁定，影响正常用户 |
| Token 泄露/共享 | 全部 | **高** | 账号冒用 |

---

## 2. 安全架构：四层防护

```
┌───────────────────────────────────────────────────────────┐
│  Layer 1: 网关层 (API Gateway)                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ • 用户认证 (OAuth 2.0 / 小程序 session)              │  │
│  │ • 全局限流 (per-IP, per-user)                        │  │
│  │ • WAF (SQL注入/XSS/异常payload)                      │  │
│  │ • Bot 检测 (设备指纹 + 行为分析)                      │  │
│  │ • TLS 终结 + 请求签名校验                             │  │
│  └─────────────────────────────────────────────────────┘  │
│                            ↓                               │
│  Layer 2: MCP 协议层 (toc_server.py)                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ • 用户身份解析 (从 gateway 注入的 header)              │  │
│  │ • 工具级权限控制 (哪些工具对哪些用户可用)               │  │
│  │ • 参数校验 + 输入消毒                                 │  │
│  │ • 敏感操作确认 (写入操作二次验证)                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                            ↓                               │
│  Layer 3: 业务风控层 (后端服务)                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ • 领券频率限制 (每用户每日上限)                        │  │
│  │ • 下单风控 (金额/频率/地址异常)                        │  │
│  │ • 积分兑换风控 (异常兑换模式检测)                      │  │
│  │ • 黄牛账号识别 + 黑名单                               │  │
│  └─────────────────────────────────────────────────────┘  │
│                            ↓                               │
│  Layer 4: 事后审计层                                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ • 全量调用日志 (user + tool + params + result)        │  │
│  │ • 异常行为告警 (高频领券/兑换/下单)                     │  │
│  │ • 资损核算 (优惠券/积分异常消耗统计)                    │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

## 3. 工具分级与防护策略

### 3.1 工具风险分级

```
L0 - 公开只读（无需登录即可用）
  browse_menu, drink_detail, nutrition_info, nearby_stores, store_detail
  → 菜单和门店信息是公开的，但仍需 IP 级限流防爬

L1 - 登录只读（需登录，读自己的数据）
  my_account, my_coupons, my_orders, delivery_addresses
  campaign_calendar, available_coupons, stars_mall_products,
  stars_product_detail, store_coupons, order_status
  → 标准认证 + per-user 限流

L2 - 登录写入（需登录，修改自己的数据，需风控）
  claim_all_coupons, create_address
  → 认证 + 限流 + 频率控制 + 人机验证

L3 - 高危写入（需登录 + 二次验证 + 强风控）
  stars_redeem, calculate_price, create_order
  → 认证 + 限流 + 人机验证 + 业务风控 + 操作确认
```

### 3.2 每个工具的具体防护

| 工具 | 级别 | 限流 | 人机验证 | 风控规则 |
|------|------|------|---------|---------|
| `browse_menu` | L0 | 60次/分/IP | - | - |
| `drink_detail` | L0 | 60次/分/IP | - | - |
| `nutrition_info` | L0 | 60次/分/IP | - | - |
| `nearby_stores` | L0 | 30次/分/IP | - | - |
| `store_detail` | L0 | 60次/分/IP | - | - |
| `campaign_calendar` | L1 | 10次/分/用户 | - | - |
| `available_coupons` | L1 | 10次/分/用户 | - | - |
| `my_account` | L1 | 10次/分/用户 | - | - |
| `my_coupons` | L1 | 10次/分/用户 | - | - |
| `my_orders` | L1 | 10次/分/用户 | - | - |
| `delivery_addresses` | L1 | 10次/分/用户 | - | - |
| `stars_mall_products` | L1 | 10次/分/用户 | - | - |
| `stars_product_detail` | L1 | 10次/分/用户 | - | - |
| `store_coupons` | L1 | 10次/分/用户 | - | - |
| `order_status` | L1 | 10次/分/用户 | - | 仅查自己的订单 |
| `claim_all_coupons` | **L2** | **3次/天/用户** | 触发时验证 | 每日领券上限 |
| `create_address` | L2 | 5次/天/用户 | - | 地址数上限10 |
| `calculate_price` | L2 | 20次/分/用户 | - | - |
| `stars_redeem` | **L3** | **5次/天/用户** | **每次验证** | 每日兑换上限+异常检测 |
| `create_order` | **L3** | **10次/天/用户** | **每次验证** | 金额/频率/地址风控 |

---

## 4. 对比 ToB — 为什么 ToB 不需要这些

| 防护维度 | ToB (不需要) | ToC (必须有) | 原因 |
|---------|-------------|-------------|------|
| 人机验证 | ✗ 对端是服务器 | ✓ 对端是人/脚本 | ToB 对端是企业级服务，不是终端用户 |
| 黄牛防控 | ✗ 合作伙伴不会薅自己的羊毛 | ✓ 必须有 | ToC 的券和积分有套利空间 |
| 工具分级 | ✗ ACL 按合作伙伴分 | ✓ 按操作风险分 | ToB 按"谁能用"分，ToC 按"多危险"分 |
| 频率控制 | 简单 QPS 即可 | 需要业务级频率 | ToB 限制 QPS 够了，ToC 要限"每天领几次" |
| 二次验证 | ✗ HMAC 签名已足够 | ✓ 高危操作需要 | ToB 的密钥就是身份证明，ToC 的 token 可能泄露 |
| IP 白名单 | ✓ 固定 IP 段 | ✗ 用户 IP 不固定 | ToB 服务器 IP 可控，ToC 用户可以在任何地方 |
| 设备指纹 | ✗ 服务器无设备概念 | ✓ 识别同设备多号 | 黄牛经典操作：一台手机切号刷券 |

---

## 5. 实现方案

### 5.1 网关层部署（推荐 Kong 或 CloudFlare）

```
ToC 用户 (App/小程序/Web)
    │
    │ HTTPS + Bearer Token (OAuth 2.0)
    ▼
┌─ Consumer Gateway (独立于 B2B Kong) ─────────────┐
│                                                    │
│  Route: /toc-mcp/*                                 │
│                                                    │
│  Plugins:                                          │
│  ├── OAuth2 Introspection (验证用户 token)          │
│  ├── Rate Limiting (per-user + per-IP 双维度)       │
│  │   ├── L0 tools: 60/min/IP                       │
│  │   ├── L1 tools: 10/min/user                     │
│  │   ├── L2 tools: custom (见上表)                  │
│  │   └── L3 tools: custom + captcha                │
│  ├── Bot Detection (设备指纹 + 行为打分)            │
│  ├── WAF (OWASP 规则集)                            │
│  └── Request Transformer (注入用户身份头)            │
│       → X-User-Id: CC_M_100001                     │
│       → X-User-Tier: GOLD                          │
│       → X-Device-Fingerprint: abc123               │
│       → X-Risk-Score: 15                           │
│                                                    │
└──────────────────┬─────────────────────────────────┘
                   ▼
          ToC MCP Server (toc_server.py)
```

### 5.2 MCP Server 层防护（代码层面）

```python
# toc_server.py 中的安全增强 (生产版本)

# 1. 用户上下文解析 — 从 gateway 注入的 header 获取身份
@mcp.tool()
def my_account(ctx: Context) -> str:
    user_id = ctx.request_context.headers.get("X-User-Id")
    if not user_id:
        return "请先登录。"
    risk_score = int(ctx.request_context.headers.get("X-Risk-Score", "0"))
    if risk_score > 80:
        return "操作异常，请稍后重试。"
    ...

# 2. L3 工具 — 前置风控检查
@mcp.tool()
def create_order(ctx: Context, store_id: str, items: list[dict], ...) -> str:
    user_id = ctx.request_context.headers["X-User-Id"]

    # 风控检查
    risk = risk_control.check_order(
        user_id=user_id,
        amount=total_price,
        device_fp=ctx.request_context.headers.get("X-Device-Fingerprint"),
        ip=ctx.request_context.headers.get("X-Real-IP"),
    )
    if risk.blocked:
        audit_log.warn("order_blocked", user_id=user_id, reason=risk.reason)
        return f"下单失败：{risk.user_message}"
    if risk.require_captcha:
        return "请完成人机验证后重试。"
    ...

# 3. 数据隔离 — 只能查自己的
@mcp.tool()
def order_status(ctx: Context, order_id: str) -> str:
    user_id = ctx.request_context.headers["X-User-Id"]
    order = backend.get_order(order_id)
    if order and order["user_id"] != user_id:
        audit_log.warn("cross_user_access", user_id=user_id, order_id=order_id)
        return "未找到该订单。"  # 不泄露订单存在
    ...
```

### 5.3 与 B2B Kong 的隔离

```
关键决策：ToC 和 ToB 使用独立的 Gateway 实例

ToB Gateway (Kong 现有)                ToC Gateway (新建)
├── HMAC-SHA256 鉴权                   ├── OAuth 2.0 / JWT
├── IP 白名单                          ├── 设备指纹 + Bot 检测
├── per-Partner QPS                    ├── per-User 业务频率
├── ACL 按 Consumer Group              ├── 工具分级 L0-L3
├── Route: /mcp, /sse                  ├── Route: /toc-mcp
└── → B2B MCP Adapter (server.py)      └── → ToC MCP Server (toc_server.py)

两套 Gateway + 两套 Server，物理隔离。
ToC 被打穿不影响 ToB 合作伙伴的服务。
```

---

## 6. 黄牛专项防控

### 6.1 领券场景 (`claim_all_coupons`)

```
防控策略：

1. 频率限制
   - 每用户每天最多调用 3 次
   - 每个设备指纹每天最多 5 次（防一机多号）
   - 新注册 24h 内账号不可领券（防批量注册）

2. 券库存保护
   - 热门券设置 per-user 领取上限（如每人限领 1 张）
   - 库存低于阈值时启用排队机制（防瞬时并发抢）
   - 活动开始前 30 秒自动启用验证码

3. 异常检测
   - 同 IP 5 分钟内 > 10 个不同账号领券 → 封 IP
   - 同设备 1 小时内 > 3 个不同账号领券 → 标记设备
   - 账号领券后从不消费 → 降低信用分
```

### 6.2 积分兑换场景 (`stars_redeem`)

```
防控策略：

1. 兑换前验证
   - 每次兑换必须通过人机验证（滑块/短信验证码）
   - 高价值商品（>200星）需要短信验证码
   - 同一商品每用户每月限兑 3 次

2. 异常检测
   - 积分突然增加（可能是盗号充值） → 冻结兑换 24h
   - 兑换后立即转赠/转卖 → 标记为疑似黄牛
   - 大量兑换同一商品 → 触发人工审核

3. 履约控制
   - 兑换券限本人使用（核销时验证手机号）
   - 实物商品限同一收货地址每月 5 件
```

### 6.3 下单场景 (`create_order`)

```
防控策略：

1. 订单风控
   - 未支付订单超过 3 笔 → 禁止新建
   - 同门店 1 小时内超过 5 笔 → 触发验证
   - 异地下单（地址距常用地址 >500km） → 提示确认

2. 优惠叠加风控
   - 同一券不可多设备并发使用（券锁定机制）
   - 异常低价订单（折扣率 >70%） → 人工审核
   - 同一优惠活动每用户每日参与上限

3. 支付风控
   - 15 分钟未支付自动取消 + 释放库存
   - 频繁创建不支付 → 降低账号权重
```

---

## 7. MCP 协议特有风险

### 7.1 长连接滥用

MCP 使用 SSE 或 Streamable HTTP 长连接。与 REST API 的短连接不同：

```
风险: 一个连接可以持续调用多个 tool，传统 per-request 限流不够
对策:
  - 连接级限流（每个连接每分钟最多 N 次 tool 调用）
  - 连接超时（空闲 5 分钟断开，最大 30 分钟）
  - 并发连接数限制（每用户最多 3 个并发 MCP 连接）
```

### 7.2 Tool 参数注入

LLM 生成的 tool 参数可能包含恶意内容：

```
风险: items 列表中注入超大 quantity、负数价格等
对策:
  - 严格参数校验（quantity 1-99，price 计算在服务端）
  - 参数白名单（size 只能是 tall/grande/venti）
  - 拒绝未知字段
```

### 7.3 Token 在 MCP 配置中的暴露

```
风险: 用户的 Bearer token 写在 .mcp.json 中，可能被版本控制/截屏泄露

.mcp.json:
{
  "mcpServers": {
    "coffee-toc": {
      "headers": {
        "Authorization": "Bearer eyJhbG..."  ← 明文 token
      }
    }
  }
}

对策:
  - Token 短期有效（2h）+ 自动刷新
  - 支持环境变量引用: "Authorization": "Bearer ${COFFEE_TOKEN}"
  - Token 绑定设备指纹，换设备失效
  - 检测到异常使用立即吊销
```

---

## 8. 总结：ToC 不是把 ToB 的门打开，是建一个新的门

```
ToB 安全模型:        ToC 安全模型:
"锁好门，只给有钥     "开着门，但每一步都
 匙的合作伙伴进"       有摄像头和保安"

┌──────────┐          ┌──────────┐
│ IP 白名单 │          │ 人机验证  │
│ HMAC 签名 │          │ 设备指纹  │
│ 合同约束  │          │ 行为风控  │
│ 企业信用  │          │ 频率限制  │
│ 年度审计  │          │ 实时监控  │
└──────────┘          └──────────┘
  边界安全                纵深防御
  (perimeter)            (defense in depth)
```

**关键原则：ToC MCP 的安全不能依赖"限制谁能接入"（因为所有消费者都能接入），
而是要靠"限制能做什么、做多少、怎么做"。**
