# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Coffee Company MCP 开放平台，提供 **B2B** 和 **ToC** 两套 MCP Server：

- **B2B Server** (`server.py`, 10 tools) — 面向合作伙伴 (蔚来/千问/飞猪)，通过 Kong 鉴权，客服/运营视角，需要传入 member_id
- **ToC Server** (`toc_server.py`, 21 tools) — 面向消费者，用户 Token 自动识别身份，自助点单/领券/积分兑换

Currently in demo mode with mock data. No real backend calls yet.

## Commands

```bash
uv sync                                    # install deps
uv run coffee-company-mcp                  # B2B MCP server (stdio)
uv run coffee-company-toc                  # ToC MCP server (stdio)
uv run coffee demo                         # 9-step B2B demo
uv run coffee interactive                  # B2B REPL mode
uv run coffee member CC_M_100001           # single B2B tool call
```

Run the full MCP protocol test suite (33 cases: tools + resources + edge cases):
```bash
uv run python tests/test_mcp_real.py
```

## Architecture

```
B2B Server (server.py)           ToC Server (toc_server.py)
10 @mcp.tool() + 2 resources     21 @mcp.tool()
    │                                 │
    ├── mock_data.py                  ├── toc_mock_data.py (imports mock_data)
    └── formatters.py                 └── toc_formatters.py
```

**B2B data flow:** MCP request → `server.py` → `mock_data.query_fn()` → `formatters.format_fn()` → markdown
**ToC data flow:** MCP request → `toc_server.py` → `toc_mock_data.query_fn()` → `toc_formatters.format_fn()` → markdown

**Key difference:** B2B tools require explicit `member_id`; ToC tools auto-resolve user from token (no ID params).

**B2B production:** Agent → Kong (HMAC auth) → B2B adapter → backend
**ToC production:** Consumer app → OAuth → ToC adapter → consumer backend

## Tool ↔ HTTP API Mapping

| Tool | HTTP Endpoint |
|------|--------------|
| `member_query` | POST /crmadapter/account/query |
| `member_tier` | POST /crmadapter/account/memberTier |
| `member_benefits` | POST /crmadapter/customers/getBenefits |
| `member_benefit_list` | POST /crmadapter/asset/coupon/getBenefitList |
| `coupon_query` | POST /coupon/query |
| `coupon_detail` | POST /coupon/detail |
| `equity_query` | POST /equity/query |
| `equity_detail` | POST /equity/detail |
| `assets_list` | POST /assets/list |
| `cashier_pay_query` | POST /cashier/payQuery |

## Demo Test Data IDs

Members: `CC_M_100001` (Gold/NIO), `CC_M_100002` (Green/Fliggy), `CC_M_100003` (Diamond/Qwen)
Coupons: `CC20260301A001`, `CC20260301A002`, `CC20260215B001`
Orders: `ORD_2026030100001`, `ORD_2026021500001`
Equity: `EQ_2026030100001`, `EQ_2026030100002`, `EQ_2026021500001`
Pay tokens: `PAY_TOKEN_001` (success), `PAY_TOKEN_002` (pending), `PAY_TOKEN_003` (failed)

## Claude Code Skills + Commands (体验层)

MCP Server 提供能力，Skills + Commands 提供体验。

### MCP Client 集成（`.mcp.json`）

```json
{
  "mcpServers": {
    "coffee-mcp": { "command": "uv", "args": ["run", ".", "coffee-company-mcp"] },
    "coffee-toc": { "command": "uv", "args": ["run", ".", "coffee-company-toc"] }
  }
}
```

### B2B Slash Commands + Skills

| Command / Skill | Description |
|---------|-------------|
| `/coffee` / `coffee` | B2B 通用助手，路由 10 个工具 |
| `/coffee-member` / `coffee-member` | 会员查询 |
| `/coffee-coupons` / `coffee-coupons` | 券码查询 |
| `/coffee-assets` / `coffee-assets` | 客户资产 |
| `/coffee-payment` / `coffee-payment` | 支付查询 |

### ToC Slash Commands + Skills

| Command / Skill | Description |
|---------|-------------|
| `/coffee-toc` / `coffee-toc` | ToC 通用助手，路由 18 个工具 |
| `/coffee-discover` / `coffee-discover` | 活动发现 + 领券 |
| `/coffee-order` / `coffee-order` | 点单流程 (选店→菜单→定制→下单) |
| `/coffee-menu` / `coffee-menu` | 菜单浏览 + 营养查询 |
| `/coffee-stars` / `coffee-stars` | 积分商城 + 兑换 |

### 工程工具

| Command / Skill | Description |
|---------|-------------|
| `/mcp-review` / `mcp-review` | MCP Tool 设计审查（10 条准则 checklist） |

### ToC 消费者旅程 (21 tools)

```
时间感知: now_time_info (LLM 获取当前时间)
发现优惠: campaign_calendar → available_coupons → claim_all_coupons
我的账户: my_account / my_coupons / my_orders
门店菜单: nearby_stores → browse_menu(compact?) → drink_detail → nutrition_info(compact?)
积分兑换: stars_mall_products → stars_product_detail → stars_redeem(idempotency_key)
下单闭环: store_coupons → calculate_price(→confirmation_token) → create_order(idempotency_key, confirmation_token) → order_status
配送地址: delivery_addresses / create_address
```

### 安全增强特性

- **确认令牌**: calculate_price 返回 confirmation_token，create_order 必须传入，防止跳过确认
- **幂等键**: L3 操作(create_order, stars_redeem)需要 idempotency_key，防止 LLM 重试导致重复操作
- **ID 随机化**: 订单/地址 ID 使用 UUID 前缀格式(ord_xxx, addr_xxx)，防止枚举攻击
- **PII 脱敏**: 地址列表中手机号自动脱敏(138****1234)
- **紧凑模式**: browse_menu 和 nutrition_info 支持 compact=True 减少 token 消耗

## Project Structure

```
.mcp.json                          # MCP client config (B2B + ToC servers)
.claude/
├── commands/                      # Slash commands
│   ├── coffee.md                  #   B2B general
│   ├── coffee-member.md           #   B2B member
│   ├── coffee-coupons.md          #   B2B coupons
│   ├── coffee-assets.md           #   B2B assets
│   ├── coffee-payment.md          #   B2B payment
│   ├── coffee-toc.md              #   ToC general
│   ├── coffee-discover.md         #   ToC discovery
│   ├── coffee-order.md            #   ToC order
│   ├── coffee-stars.md            #   ToC stars mall
│   └── mcp-review.md             #   MCP tool design review
└── skills/                        # Natural language auto-trigger
    ├── coffee/                    #   B2B skills...
    ├── coffee-toc/                #   ToC general
    ├── coffee-discover/           #   ToC discovery
    ├── coffee-order/              #   ToC order flow
    ├── coffee-menu/               #   ToC menu browse
    ├── coffee-stars/              #   ToC stars mall
    └── mcp-review/               #   MCP tool design review
docs/
└── MCP_API_DESIGN_GUIDE.md        # MCP 接口设计准则（完整版）
src/coffee_mcp/
├── server.py                      # B2B MCP Server (10 tools)
├── toc_server.py                  # ToC MCP Server (18 tools)
├── mock_data.py                   # B2B mock data
├── toc_mock_data.py               # ToC mock data (stores, menu, orders, stars mall)
├── formatters.py                  # B2B formatters
├── toc_formatters.py              # ToC formatters
├── cli.py                         # Click CLI + REPL
└── __init__.py
```

## Code Conventions

- Chinese user-facing strings in tool responses; English in code/comments
- Python 3.13 union syntax (`str | None`, not `Optional[str]`)
- Every tool returns a formatted markdown string, never raw JSON
- `mock_data.py` functions mirror the real API response shapes — when replacing with real HTTP calls, keep the same return types
