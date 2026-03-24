# Coffee Company ToC MCP 平台方案

> 面向消费者的 MCP 开放平台设计方案
> 版本：v1.0 | 日期：2026-03-24

---

## 一、定位与目标

### 1.1 是什么

Coffee Company ToC MCP Server 是一个面向消费者的 AI 原生点单平台。消费者通过 AI 助手（OpenClaw / Claude Desktop / Cursor 等 MCP 客户端）以自然语言完成**发现优惠 → 浏览菜单 → 下单支付 → 查看订单**的完整闭环。

### 1.2 不是什么

- 不是传统 REST API — 工具描述即路由，LLM 根据 description 选择工具，不需要前端代码
- 不是 B2B 开放平台 — B2B Server 面向合作伙伴（蔚来/千问/飞猪），需要 Kong HMAC 鉴权和显式 `member_id`
- 不是麦当劳方案的复制 — 在安全分级、鉴权模型、幂等性等方面做了本质提升

### 1.3 与麦当劳 MCP 的核心差异

| 维度 | 麦当劳 MCP | Coffee Company ToC |
|------|-----------|-------------------|
| 安全分级 | 无分级，统一 600/min | L0-L3 四级差异化限流 |
| 鉴权 | 用户手动复制 Bearer Token | OAuth 2.0 + 网关注入，用户无感 |
| 写操作保护 | 无确认机制 | 确认令牌 + 幂等 key |
| B2B/ToC 分离 | 无 B2B 层 | 独立双 Server，权限模型隔离 |
| 传输协议 | 仅远程 HTTP | stdio + Streamable HTTP 双模 |
| 客户端生态 | 通用 MCP 客户端 | OpenClaw 深度集成 + Skill 体验层 |

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        消费者触达层                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │ 微信/飞书 │  │ WhatsApp │  │ Telegram │  │ macOS/iOS/Android│    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬──────────┘    │
│       └──────────────┼──────────────┼───────────────┘               │
│                      ▼                                              │
│              ┌───────────────┐                                      │
│              │   OpenClaw    │  ← AI 助手（MCP Client）              │
│              │  Agent + SDK  │                                      │
│              └───────┬───────┘                                      │
└──────────────────────┼──────────────────────────────────────────────┘
                       │  MCP Protocol (stdio / Streamable HTTP)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        网关层 (Kong / CloudFlare)                     │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌───────────────────┐   │
│  │ OAuth 2.0  │ │ 全局限流    │ │ WAF/Bot  │ │ Header 注入        │   │
│  │ Token 校验 │ │ per-IP     │ │ 检测     │ │ X-User-Id          │   │
│  │            │ │ per-User   │ │          │ │ X-User-Tier        │   │
│  │            │ │            │ │          │ │ X-Device-Fingerprint│   │
│  │            │ │            │ │          │ │ X-Risk-Score       │   │
│  └────────────┘ └────────────┘ └──────────┘ └───────────────────┘   │
└──────────────────────┬───────────────────────────────────────────────┘
                       │  HTTP (内网)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  ToC MCP Server (toc_server.py)                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ 19 @mcp.tool()                                                  │ │
│  │                                                                 │ │
│  │  L0 公开只读    L1 认证只读    L2 认证写入     L3 高危写入        │ │
│  │  ─────────     ─────────     ─────────      ─────────          │ │
│  │  nearby_stores  my_account   claim_all      create_order       │ │
│  │  store_detail   my_coupons   create_address stars_redeem       │ │
│  │  browse_menu    my_orders    ·              ·                  │ │
│  │  drink_detail   delivery_addr               ·                  │ │
│  │  nutrition_info store_coupons                                   │ │
│  │  now_time_info  stars_mall                                      │ │
│  │  ·              stars_detail                                    │ │
│  │  ·              calculate_price                                 │ │
│  │  ·              campaign_cal                                    │ │
│  │  ·              available_coupons                               │ │
│  │  ·              order_status                                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                          │                                           │
│                          ▼                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │ toc_mock_data.py │  │ toc_formatters.py│  │ rate_limiter      │  │
│  │ (demo) / HTTP    │  │ markdown 输出     │  │ (Redis in prod)  │  │
│  │ adapter (prod)   │  │                  │  │                   │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                       │
                       ▼  (生产环境)
┌──────────────────────────────────────────────────────────────────────┐
│                     消费者后端微服务                                   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │
│  │ 会员   │ │ 券码   │ │ 菜单   │ │ 订单   │ │ 积分   │            │
│  │ 服务   │ │ 服务   │ │ 服务   │ │ 服务   │ │ 服务   │            │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘            │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 三、用户鉴权方案

### 3.1 鉴权模型总览

采用 **OAuth 2.0 + 网关注入** 模型，用户无需手动复制 token（区别于麦当劳的手动复制方式）。

```
┌───────────────────────────────────────────────────────────────┐
│                     首次授权流程                                │
│                                                               │
│  用户 ──► OpenClaw ──► Coffee OAuth 授权页 ──► 用户同意        │
│                              │                                │
│                              ▼                                │
│                    颁发 access_token + refresh_token           │
│                              │                                │
│                              ▼                                │
│                    OpenClaw 安全存储 token                      │
│                    (Keychain / 加密存储)                        │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     每次请求流程                                │
│                                                               │
│  用户 "帮我点杯拿铁"                                           │
│    │                                                          │
│    ▼                                                          │
│  OpenClaw Agent 选择 browse_menu 工具                          │
│    │                                                          │
│    ▼                                                          │
│  MCP 请求 + Authorization: Bearer {access_token}              │
│    │                                                          │
│    ▼                                                          │
│  Kong 网关：                                                   │
│    1. 校验 token 有效性（introspect / JWT verify）             │
│    2. 解析用户身份 → X-User-Id: CC_M_100001                   │
│    3. 查询用户等级 → X-User-Tier: GOLD                        │
│    4. 计算风险分 → X-Risk-Score: 15                           │
│    5. 提取设备指纹 → X-Device-Fingerprint: abc123             │
│    │                                                          │
│    ▼                                                          │
│  ToC MCP Server 读取 header，执行工具逻辑                      │
│  （工具代码中无需传入 user_id，网关已注入）                      │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 Token 生命周期

| 阶段 | 说明 |
|------|------|
| 颁发 | 用户通过 OAuth 授权页登录（手机验证码 / 微信扫码） |
| 存储 | OpenClaw 加密存储在设备本地（macOS Keychain / Android Keystore） |
| 使用 | 每次 MCP 请求自动附带 `Authorization: Bearer xxx` |
| 刷新 | access_token 过期后，OpenClaw 自动用 refresh_token 续期 |
| 吊销 | 用户在 App 中"退出登录"或"解除 AI 助手绑定" |

### 3.3 Token 作用域（Scope）

不是所有工具都需要完整权限。按最小权限原则设计 scope：

| Scope | 覆盖工具 | 说明 |
|-------|---------|------|
| `menu:read` | browse_menu, drink_detail, nutrition_info, nearby_stores, store_detail | 公开信息，无需登录也可用 |
| `account:read` | my_account, my_coupons, my_orders, delivery_addresses, order_status | 读取个人数据 |
| `coupon:write` | claim_all_coupons, available_coupons, campaign_calendar | 领券操作 |
| `order:write` | calculate_price, create_order, store_coupons | 下单操作 |
| `stars:write` | stars_mall_products, stars_product_detail, stars_redeem | 积分兑换 |
| `address:write` | create_address | 地址管理 |

**默认授权**：首次连接请求 `menu:read account:read coupon:write`，下单时增量请求 `order:write`。

### 3.4 与麦当劳鉴权对比

| 维度 | 麦当劳 | Coffee Company |
|------|--------|---------------|
| 获取方式 | 用户登录网页 → 手动复制 token | OAuth 授权 → 自动存储 |
| 安全性 | token 暴露在剪贴板，可截获 | 加密存储，不经过剪贴板 |
| 续期 | 未知（可能需要重新登录） | refresh_token 自动续期 |
| 权限粒度 | 全量权限 | scope 最小权限 |
| 多设备 | 每个设备重新复制 | OAuth 独立授权，互不影响 |

---

## 四、工具清单（19 Tools）

### 4.1 完整工具列表

#### L0 — 公开只读（无需登录）

限流：60/min per IP

| 工具 | 参数 | 说明 |
|------|------|------|
| `now_time_info` | 无 | 返回当前日期时间和星期，供 LLM 判断活动有效期 |
| `nearby_stores` | `city?: str`, `keyword?: str` | 按城市/关键词搜索门店 |
| `store_detail` | `store_id: str` | 门店详情（营业时间、服务、设施） |
| `browse_menu` | `store_id: str` | 指定门店的菜单（品类 + 价格） |
| `drink_detail` | `product_code: str` | 饮品定制选项（杯型/奶/加料） |
| `nutrition_info` | `product_code: str` | 营养信息（热量/蛋白质/脂肪） |

#### L1 — 认证只读（需登录）

限流：30/min per user

| 工具 | 参数 | 说明 |
|------|------|------|
| `campaign_calendar` | `month?: str` | 当月活动日历 |
| `available_coupons` | 无 | 可领取的优惠券列表 |
| `my_account` | 无 | 我的账户（等级/星星/权益数） |
| `my_coupons` | `status?: "valid"\|"used"` | 我的优惠券 |
| `my_orders` | `limit?: int = 5` | 最近订单 |
| `delivery_addresses` | 无 | 我的配送地址 |
| `store_coupons` | `store_id: str` | 指定门店可用的优惠券 |
| `calculate_price` | `store_id, items[], coupon_code?` | 试算价格（含折扣） |
| `stars_mall_products` | `category?: str` | 积分商城商品列表 |
| `stars_product_detail` | `product_code: str` | 积分商品详情 |
| `order_status` | `order_id: str` | 订单状态（仅可查自己的） |

#### L2 — 认证写入

限流：5/hour per user

| 工具 | 参数 | 说明 |
|------|------|------|
| `claim_all_coupons` | 无 | 一键领取所有可领优惠券 |
| `create_address` | `city, address, address_detail, contact_name, phone` | 新增配送地址（最多 10 个） |

#### L3 — 高危写入

限流：10/day per user

| 工具 | 参数 | 说明 |
|------|------|------|
| `create_order` | `store_id, items[], pickup_type, idempotency_key, confirmation_token, coupon_code?, address_id?` | 创建订单（需确认令牌） |
| `stars_redeem` | `product_code: str, idempotency_key: str` | 积分兑换（需确认令牌） |

### 4.2 相比上一版新增

| 变更 | 说明 |
|------|------|
| **+** `now_time_info` | 学习麦当劳，解决 LLM 不知道当前时间的问题 |
| **+** `idempotency_key` | L3 工具新增幂等键，防止 LLM 重试导致重复下单 |
| **+** `confirmation_token` | L3 工具需要前置工具返回的确认令牌，防止跳过确认 |

---

## 五、消费者旅程：通过 OpenClaw 点单

### 5.1 接入配置

#### 方式一：stdio（本地开发 / Claude Desktop / Cursor）

```json
// .mcp.json 或 claude_desktop_config.json
{
  "mcpServers": {
    "coffee-toc": {
      "command": "uv",
      "args": ["run", "coffee-company-toc"],
      "env": {
        "COFFEE_USER_TOKEN": "用户的 access_token"
      }
    }
  }
}
```

#### 方式二：Streamable HTTP（OpenClaw / 远程客户端）

```python
# OpenClaw SDK 配置
from openclaw_sdk import McpServer

coffee_server = McpServer.http(
    url="https://mcp.coffeecompany.com/toc",
    headers={
        "Authorization": f"Bearer {user_access_token}"
    }
)

agent.add_mcp_server(coffee_server)
```

#### 方式三：OpenClaw Skill 配置（推荐）

```yaml
# ~/.openclaw/skills/coffee-order/SKILL.md
---
name: Coffee Company 点单助手
mcp_servers:
  - url: https://mcp.coffeecompany.com/toc
    auth: oauth
    oauth_config:
      authorization_url: https://auth.coffeecompany.com/oauth/authorize
      token_url: https://auth.coffeecompany.com/oauth/token
      client_id: openclaw_coffee_client
      scopes:
        - menu:read
        - account:read
        - coupon:write
        - order:write
---

你是 Coffee Company 的点单助手。帮助用户浏览菜单、选择饮品、使用优惠券、下单点餐。

## 点单流程
1. 先调用 now_time_info 确认当前时间
2. 用 nearby_stores 找到用户附近的门店
3. 用 browse_menu 展示菜单
4. 用 drink_detail 展示定制选项
5. 用 store_coupons 检查可用优惠
6. 用 calculate_price 试算价格，展示给用户确认
7. 用户确认后，用 create_order 下单
8. 返回订单详情和支付链接
```

### 5.2 完整点单旅程

以用户张三通过 OpenClaw (微信) 点单为例：

```
用户（微信）                  OpenClaw Agent               Coffee ToC MCP Server
    │                              │                              │
    │  "帮我点杯咖啡"              │                              │
    │ ────────────────────────►    │                              │
    │                              │                              │
    │                              │  ① now_time_info()           │
    │                              │ ─────────────────────────►   │
    │                              │  "2026-03-24 14:30 周二"     │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │                              │  ② nearby_stores(city="上海") │
    │                              │ ─────────────────────────►   │
    │                              │  [环球港店, 中山公园店, ...]   │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │  "您附近有这些门店：          │                              │
    │   1. 环球港店 (500m)         │                              │
    │   2. 中山公园店 (1.2km)      │                              │
    │   去哪家？"                  │                              │
    │ ◄────────────────────────    │                              │
    │                              │                              │
    │  "环球港"                    │                              │
    │ ────────────────────────►    │                              │
    │                              │                              │
    │                              │  ③ browse_menu(store_id=     │
    │                              │     "SH001")                 │
    │                              │ ─────────────────────────►   │
    │                              │  [经典咖啡, 季节限定, ...]    │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │  "环球港店菜单：              │                              │
    │   ☕ 经典拿铁 ¥36             │                              │
    │   ☕ 燕麦拿铁 ¥42             │                              │
    │   🌸 樱花拿铁(季节限定) ¥45  │                              │
    │   想喝什么？"                │                              │
    │ ◄────────────────────────    │                              │
    │                              │                              │
    │  "燕麦拿铁 大杯 少冰"        │                              │
    │ ────────────────────────►    │                              │
    │                              │                              │
    │                              │  ④ drink_detail(product_code │
    │                              │     ="OATLATTE")             │
    │                              │ ─────────────────────────►   │
    │                              │  杯型/温度/加料选项           │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │                              │  ⑤ store_coupons(store_id=  │
    │                              │     "SH001")                 │
    │                              │ ─────────────────────────►   │
    │                              │  [满40减5, 燕麦系列9折]       │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │                              │  ⑥ calculate_price(          │
    │                              │     store_id="SH001",        │
    │                              │     items=[{OATLATTE,venti}],│
    │                              │     coupon="OAT_90_OFF")     │
    │                              │ ─────────────────────────►   │
    │                              │  原价¥46, 优惠-¥4.6,         │
    │                              │  应付¥41.4                   │
    │                              │  confirmation_token=         │
    │                              │    "cfm_a7f3b2e9"            │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │  "帮你算好了：                │                              │
    │   燕麦拿铁 大杯 少冰          │                              │
    │   原价 ¥46 → 优惠后 ¥41.4   │                              │
    │   (已用 燕麦系列9折券)        │                              │
    │   确认下单吗？"              │                              │
    │ ◄────────────────────────    │                              │
    │                              │                              │
    │  "确认"                      │                              │
    │ ────────────────────────►    │                              │
    │                              │                              │
    │                              │  ⑦ create_order(             │
    │                              │     store_id="SH001",        │
    │                              │     items=[...],             │
    │                              │     pickup_type="自提",       │
    │                              │     coupon_code="OAT_90_OFF",│
    │                              │     idempotency_key=         │
    │                              │       "idem_x9y2z7",         │
    │                              │     confirmation_token=      │
    │                              │       "cfm_a7f3b2e9")        │
    │                              │ ─────────────────────────►   │
    │                              │  订单已创建                   │
    │                              │  order_id=ord_8k2m4n         │
    │                              │  payment_url=...             │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │  "下单成功！                  │                              │
    │   订单号：ord_8k2m4n         │                              │
    │   请点击链接完成支付 →        │                              │
    │   预计 10 分钟后可取"        │                              │
    │ ◄────────────────────────    │                              │
    │                              │                              │
    │  (支付完成后)                 │                              │
    │  "做好了吗？"                │                              │
    │ ────────────────────────►    │                              │
    │                              │                              │
    │                              │  ⑧ order_status(             │
    │                              │     order_id="ord_8k2m4n")   │
    │                              │ ─────────────────────────►   │
    │                              │  状态：制作中                 │
    │                              │ ◄─────────────────────────   │
    │                              │                              │
    │  "正在制作中，预计还需         │                              │
    │   5 分钟，稍等哦~"           │                              │
    │ ◄────────────────────────    │                              │
```

### 5.3 其他消费旅程

#### 优惠发现旅程

```
now_time_info → campaign_calendar → available_coupons → claim_all_coupons → my_coupons
       │                │                  │                   │              │
   确认当前时间     查看当月活动       浏览可领优惠券       一键全部领取    查看已领券
```

#### 积分兑换旅程

```
my_account → stars_mall_products → stars_product_detail → stars_redeem
     │               │                     │                   │
  查看星星余额    浏览积分商城         查看兑换详情          确认兑换
```

#### 外送点单旅程

```
delivery_addresses → (create_address) → nearby_stores → browse_menu → ...
        │                  │                  │              │
   查看已有地址      新增地址(如需)      搜索可配送门店     选品下单
                                                             │
                                                    create_order(
                                                      pickup_type="外送",
                                                      address_id="addr_xxx"
                                                    )
```

---

## 六、安全设计

### 6.1 四层防御体系

```
Layer 1: 网关层 (Kong / CloudFlare)
├── OAuth 2.0 token 校验
├── 全局限流（per-IP, per-User）
├── WAF + Bot 检测
├── 设备指纹提取
└── 风险评分计算

Layer 2: MCP 协议层 (toc_server.py)
├── L0-L3 工具分级限流
├── 白名单参数校验
├── 确认令牌验证（L3）
├── 幂等 key 去重（L3）
└── 用户数据隔离

Layer 3: 业务规则层
├── 每人最多 10 个地址
├── 每单最多 20 杯
├── 单杯数量 1-99
├── 手机号格式校验 (^1\d{10}$)
└── 门店营业状态校验

Layer 4: 审计层
├── 全链路操作日志
├── 异常行为告警
├── 黄牛行为识别
└── 合规审计追踪
```

### 6.2 工具限流策略

| 安全级别 | 限流规则 | 维度 | 适用工具 |
|---------|---------|------|---------|
| L0 公开只读 | 60/min | per-IP | nearby_stores, browse_menu, drink_detail, nutrition_info, store_detail, now_time_info |
| L1 认证只读 | 30/min | per-User | my_account, my_coupons, my_orders 等 |
| L2 认证写入 | 5/hour | per-User | claim_all_coupons, create_address |
| L3 高危写入 | 10/day | per-User | create_order, stars_redeem |

**生产环境**：Redis 滑动窗口限流，支持水平扩展。

### 6.3 确认令牌机制（L3 保护）

防止 LLM 跳过价格确认直接下单：

```
                calculate_price()
                      │
                      ▼
            返回 confirmation_token
            (有效期 5 分钟, 一次性)
                      │
                      ▼
              用户确认价格
                      │
                      ▼
    create_order(confirmation_token="cfm_xxx")
                      │
                      ▼
           服务端验证 token:
           ├── 存在？ → 继续
           ├── 过期？ → "请重新试算价格"
           ├── 已使用？ → "请重新试算价格"
           └── 金额不匹配？ → "价格已变动，请重新试算"
```

### 6.4 幂等性保护（防重复下单）

```python
# LLM 网络超时 → 自动重试 → 重复下单
# 幂等 key 解决方案：

# 请求 1:
create_order(idempotency_key="idem_x9y2z7", ...)  → 创建订单 ord_8k2m4n

# 请求 2 (重试):
create_order(idempotency_key="idem_x9y2z7", ...)  → 返回已有订单 ord_8k2m4n (不重复创建)
```

**实现**：Redis `SETNX` + TTL 24h，key 格式 `idem:{user_id}:{idempotency_key}`。

### 6.5 数据安全

| 措施 | 说明 |
|------|------|
| **用户隔离** | order_status 仅返回自己的订单，查不到返回"未找到"（不泄露存在性） |
| **ID 随机化** | 订单/地址/券码使用随机 ID（`ord_8k2m4n`），不可枚举 |
| **PII 脱敏** | 列表场景手机号显示 `152****5678`，详情场景完整展示 |
| **Scope 隔离** | 未授权 scope 的工具调用返回 401，不暴露工具存在 |

### 6.6 威胁模型与应对

| 威胁 | 攻击方式 | 防御措施 |
|------|---------|---------|
| **黄牛刷券** | 自动化调用 claim_all_coupons | L2 限流 5/hour + 设备指纹 + 风险评分 |
| **积分套利** | 脚本批量兑换限量商品 | L3 限流 10/day + 确认令牌 + captcha (risk_score > 80) |
| **订单轰炸** | 大量创建未支付订单锁库存 | L3 限流 + 未支付订单上限 3 个 |
| **数据爬取** | 遍历门店/菜单/营养数据 | L0 限流 60/min per-IP + WAF Bot 检测 |
| **Token 泄露** | 用户 token 被截获 | OAuth scope 最小化 + refresh_token 轮换 + 异常 IP 告警 |
| **跨用户访问** | 篡改 user_id 查看他人数据 | 网关注入 X-User-Id，MCP 层不接受客户端传入 |

---

## 七、传输协议：双模设计

### 7.1 stdio 模式（开发/本地客户端）

```
┌──────────────────┐     stdin/stdout      ┌──────────────────┐
│  Claude Desktop  │ ◄──── JSON-RPC ────►  │  ToC MCP Server  │
│  / Cursor        │                       │  (本地进程)       │
└──────────────────┘                       └──────────────────┘
```

**优势**：低延迟、无网络依赖、简单调试
**适用**：开发测试、Claude Desktop、Cursor

### 7.2 Streamable HTTP 模式（OpenClaw/远程客户端）

```
┌──────────────────┐       HTTPS          ┌──────────┐       ┌──────────────────┐
│  OpenClaw        │ ◄── JSON-RPC ──►     │  Kong    │ ──►   │  ToC MCP Server  │
│  (任意设备)       │     + Bearer Token   │  网关    │       │  (云端集群)       │
└──────────────────┘                      └──────────┘       └──────────────────┘
```

**优势**：零安装、多设备、可水平扩展
**适用**：OpenClaw、移动端、Web 集成

### 7.3 FastMCP 双模实现

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("coffee-toc")

# 所有工具定义不变，传输由启动参数决定：

# stdio 模式
# $ uv run coffee-company-toc

# HTTP 模式
# $ uv run coffee-company-toc --transport streamable-http --port 8080
```

---

## 八、OpenClaw 深度集成

### 8.1 Skill 生态

在 ClawHub 发布 Coffee Company 官方 Skill，用户一键安装：

```bash
# 用户安装
openclaw skills install coffee-company-order

# 或通过 McPorter
mcporter install coffee-company-toc --target openclaw
```

### 8.2 Skill 体系设计

| Skill | 触发语 | 路由工具 |
|-------|--------|---------|
| `coffee-order` | "帮我点杯咖啡"、"下单" | nearby_stores → browse_menu → calculate_price → create_order |
| `coffee-discover` | "有什么优惠"、"帮我领券" | campaign_calendar → available_coupons → claim_all_coupons |
| `coffee-stars` | "积分换什么"、"用星星兑换" | my_account → stars_mall_products → stars_redeem |
| `coffee-menu` | "菜单"、"有什么新品"、"热量多少" | browse_menu → drink_detail → nutrition_info |

### 8.3 多渠道触达

```
OpenClaw 平台能力
    │
    ├── 微信 ← "帮我点杯燕麦拿铁"
    ├── 飞书 ← "查一下我的星星余额"
    ├── WhatsApp ← "order a latte please"
    ├── Telegram ← "附近有什么店"
    ├── macOS App ← 桌面端完整体验
    ├── iOS App ← 移动端
    └── Web ← 浏览器接入
```

用户在**任意渠道**发送自然语言，OpenClaw Agent 调用 Coffee ToC MCP Server 完成操作，体验一致。

---

## 九、响应格式优化

### 9.1 Token 成本意识

LLM 场景下，每次工具返回都消耗 token（真金白银）。参考麦当劳的紧凑格式：

```
# 标准模式（默认）
## 🥤 燕麦拿铁 Oat Latte
- **价格**：¥36 / ¥42 / ¥46（中/大/超大）
- **热量**：180 / 240 / 310 kcal
- **特色**：澳洲进口燕麦奶，丝滑口感

# 紧凑模式（高频/批量场景）
燕麦拿铁|36/42/46|180/240/310kcal|燕麦奶
```

### 9.2 实现方式

工具支持 `compact` 参数控制输出密度：

```python
@mcp.tool()
def browse_menu(store_id: str, compact: bool = False) -> str:
    """浏览指定门店的菜单"""
    data = toc_mock_data.get_store_menu(store_id)
    if compact:
        return toc_formatters.format_menu_compact(data)
    return toc_formatters.format_menu(data)
```

**Skill 层控制**：首次浏览用标准模式展示详情，后续筛选/对比用紧凑模式节省 token。

---

## 十、生产化路线

### Phase 1 — 安全加固（Week 1-2）

- [ ] 资源 ID 随机化（UUID 替代顺序 ID）
- [ ] PII 脱敏（手机号/地址列表场景）
- [ ] 添加 `now_time_info` 工具
- [ ] L3 工具添加 `idempotency_key` 参数
- [ ] L3 工具添加 `confirmation_token` 机制

### Phase 2 — 基础设施（Week 3-4）

- [ ] Redis 滑动窗口限流替代内存限流
- [ ] 审计日志（结构化日志 + ELK）
- [ ] Streamable HTTP 传输模式
- [ ] OAuth 2.0 授权服务搭建
- [ ] Kong 网关配置（Token 校验 + Header 注入）

### Phase 3 — 体验优化（Week 5-6）

- [ ] 响应紧凑模式（`compact` 参数）
- [ ] OpenClaw Skill 开发 + ClawHub 发布
- [ ] 多语言支持（中/英）
- [ ] 用户反馈闭环（订单评价工具）

### Phase 4 — 风控上线（Week 7-8）

- [ ] 设备指纹集成
- [ ] 风险评分模型
- [ ] L3 操作 captcha/2FA
- [ ] 黄牛行为识别 + 自动封禁
- [ ] 异常告警（Grafana + PagerDuty）

### Phase 5 — 生态扩展（后续）

- [ ] Claude Desktop / Cursor 官方集成
- [ ] 企业微信 / 钉钉渠道
- [ ] 语音点单（OpenClaw 语音模式）
- [ ] 推荐引擎（基于历史订单）
- [ ] A/B 测试框架（工具描述优化）

---

## 附录

### A. 工具 ↔ HTTP API 映射（生产环境）

| MCP Tool | HTTP Endpoint | Method |
|----------|--------------|--------|
| `now_time_info` | 本地计算 | — |
| `nearby_stores` | `/consumer/stores/nearby` | POST |
| `store_detail` | `/consumer/stores/{store_id}` | GET |
| `browse_menu` | `/consumer/menu/{store_id}` | GET |
| `drink_detail` | `/consumer/products/{product_code}` | GET |
| `nutrition_info` | `/consumer/products/{product_code}/nutrition` | GET |
| `campaign_calendar` | `/consumer/campaigns` | GET |
| `available_coupons` | `/consumer/coupons/available` | GET |
| `claim_all_coupons` | `/consumer/coupons/claim-all` | POST |
| `my_account` | `/consumer/account` | GET |
| `my_coupons` | `/consumer/coupons/mine` | GET |
| `my_orders` | `/consumer/orders` | GET |
| `delivery_addresses` | `/consumer/addresses` | GET |
| `create_address` | `/consumer/addresses` | POST |
| `store_coupons` | `/consumer/stores/{store_id}/coupons` | GET |
| `calculate_price` | `/consumer/orders/calculate` | POST |
| `create_order` | `/consumer/orders` | POST |
| `order_status` | `/consumer/orders/{order_id}` | GET |
| `stars_mall_products` | `/consumer/stars-mall/products` | GET |
| `stars_product_detail` | `/consumer/stars-mall/products/{code}` | GET |
| `stars_redeem` | `/consumer/stars-mall/redeem` | POST |

### B. 错误码规范

| HTTP Code | MCP 层含义 | 用户提示 |
|-----------|-----------|---------|
| 200 | 成功 | （正常返回 markdown） |
| 401 | Token 无效/过期 | "登录已过期，请重新授权" |
| 403 | Scope 不足 | "需要额外授权才能执行此操作" |
| 429 | 限流 | "操作过于频繁，请稍后再试" |
| 409 | 幂等冲突（已存在） | 返回已有结果（不报错） |
| 422 | 参数校验失败 | 具体错误信息（如"手机号格式无效"） |
| 500 | 服务器内部错误 | "系统繁忙，请稍后再试" |

### C. 与竞品对比总结

| 维度 | 麦当劳 MCP | Coffee Company ToC | 优势方 |
|------|-----------|-------------------|--------|
| 安全分级 | 无 | L0-L3 四级 | Coffee |
| 鉴权 | 手动复制 Token | OAuth 自动管理 | Coffee |
| 幂等性 | 无 | idempotency_key | Coffee |
| 确认机制 | 依赖客户端 | confirmation_token | Coffee |
| 时间感知 | now-time-info | now_time_info | 持平 |
| Token 优化 | 紧凑格式 | compact 模式 | 持平 |
| 接入门槛 | 零安装(远程HTTP) | 双模(stdio+HTTP) | 持平 |
| 上线速度 | 2025.12 已上线 | 设计中 | 麦当劳 |
