# 星巴克中国 MCP Server 技术方案

**文档版本**：v1.0  
**作者**：SITC Digital Trading Team  
**日期**：2026-03  
**状态**：草稿

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [核心架构设计](#2-核心架构设计)
3. [鉴权方案](#3-鉴权方案)
4. [MCP Tools 清单](#4-mcp-tools-清单)
5. [与主流 CLI 的关系](#5-与主流-cli-的关系)
6. [分阶段落地计划](#6-分阶段落地计划)
7. [技术实现细节](#7-技术实现细节)
8. [部署架构](#8-部署架构)
9. [资源与成本估算](#9-资源与成本估算)
10. [战略价值](#10-战略价值)

---

## 1. 背景与目标

### 1.1 为什么现在做

随着 MCP（Model Context Protocol）协议成为 AI Agent 与外部服务交互的事实标准，各主要平台（Claude Code、Cursor、Claude Desktop、Copilot）已原生支持 MCP Client 能力。高德地图于 2025 年 3 月率先推出 MCP Server，以位置服务接入 AI Agent 生态，验证了这一路径的可行性。

**星巴克的差异化机会**：高德只能提供**信息查询**，星巴克可以通过 MCP 完成**真实交易闭环**——这是质的跃升。

### 1.2 目标

- **短期**：基于现有开放平台 API（`openapi.starbucks.com.cn`），以最小改造快速上线 MCP Server
- **中期**：支持 AI Agent 完整点单流程，接入主流 MCP Marketplace
- **长期**：成为 Agent Economy 中餐饮零售领域的标准服务节点

### 1.3 设计原则

| 原则 | 说明 |
|---|---|
| **薄适配** | MCP 层仅做协议转换，不重建业务逻辑 |
| **零侵入** | 现有开放平台 API 不做任何改造 |
| **鉴权复用** | 完全复用开放平台现有 API Key 体系 |
| **语义优先** | 对 JSON 响应做自然语言转换，让 LLM 更好理解 |
| **渐进开放** | 只读 Tool 先行，授权交易 Tool 后续跟进 |

---

## 2. 核心架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent / MCP Client 层                  │
│                                                             │
│   Claude Code CLI    Cursor    Claude Desktop    自研 Agent  │
│         └──────────────┴───────────┴──────────────┘         │
│                      MCP Protocol                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
              SSE / Streamable HTTP
              https://mcp.starbucks.com.cn
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   MCP Adapter Layer（新建）                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Tool Registry  │  语义化转换层  │  Auth Passthrough  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  门店    │  │  菜单    │  │  库存    │  │  下单    │   │
│  │  Tools   │  │  Tools   │  │  Tools   │  │  Tools   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │  原有 HTTPS + API Key（不变）
                            ▼
              openapi.starbucks.com.cn
              （现有开放平台，零改造）
```

### 2.2 数据流

```
1. AI Agent 携带 API Key 连接 MCP Endpoint
2. Agent 调用 Tool（如 search_nearby_stores）
3. MCP Adapter 将 Tool 参数转换为开放平台 REST 请求
4. 透传 API Key 至开放平台做鉴权
5. 开放平台返回原始 JSON
6. MCP Adapter 做语义化转换（JSON → 自然语言描述）
7. 返回结构化文本给 AI Agent
```

---

## 3. 鉴权方案

### 3.1 核心策略：完全透传，零新增

MCP Adapter 不做任何鉴权判断，**将 API Key 原样透传**给开放平台。开放平台返回 401/403 时，MCP 层直接抛出 McpError，等于完全沿用现有的 Key 管理、权限分级、限流策略。

```
AI Agent → MCP Endpoint（携带 key）
               ↓ 透传
         openapi.starbucks.com.cn（验证 key）
               ↓ 返回 401/403
         MCP Adapter → McpError → AI Agent
```

### 3.2 三种接入姿势（全部兼容现有 Key）

**姿势 1：URL Param（最简单，对标高德）**
```json
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/sse?key=YOUR_API_KEY"
    }
  }
}
```

**姿势 2：HTTP Header（更安全，Key 不出现在日志 URL 里）**
```json
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/sse",
      "headers": { "Authorization": "Bearer YOUR_API_KEY" }
    }
  }
}
```

**姿势 3：Streamable HTTP（未来主流）**
```json
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/mcp?key=YOUR_API_KEY"
    }
  }
}
```

三种姿势底层打向开放平台的 HTTP 请求格式**完全不变**。

### 3.3 权限分级评估

| 现有开放平台 Key 类型 | MCP 层处理策略 |
|---|---|
| 已有只读/下单权限分级 | 直接复用，零改造 |
| 单一全量权限 | MCP 层按 Tool 名称做白名单，限制危险接口调用 |
| 需要用户级 OAuth（会员下单） | 只读 Tool 走 API Key；下单 Tool 单独加 OAuth flow（Phase 2） |

**Phase 1 快速上线建议**：只开放只读 Tool（门店搜索、菜单查询），现有 Key 体系 **0 改造**，两周内可跑通。

---

## 4. MCP Tools 清单

### 4.1 Phase 1：只读 Tools（无需额外授权）

| Tool Name | 对应开放平台 API | 典型 LLM 调用场景 |
|---|---|---|
| `search_nearby_stores` | 门店搜索 | "帮我找附近的星巴克" |
| `get_store_detail` | 门店详情 | "这家门店几点关门，有没有座位" |
| `get_menu` | 产品菜单 | "最近有什么新品，有没有燕麦奶选项" |
| `get_product_detail` | 单品详情 + 定制选项 | "馥芮白能加燕麦奶吗，有几个杯型" |
| `check_store_inventory` | 门店库存状态 | "这杯今天有没有货" |
| `get_promotions` | 当前促销活动 | "现在有什么买一送一活动" |

### 4.2 Phase 2：交易 Tools（需 OAuth 授权）

| Tool Name | 对应开放平台 API | 典型 LLM 调用场景 |
|---|---|---|
| `create_order` | 下单接口 | "帮我点一杯大杯燕麦拿铁少冰" |
| `get_rewards_info` | 会员星享卡权益 | "我现在有多少星星，离下一级还差多少" |
| `send_gift_order` | 礼品券 / 电子礼品卡 | "帮我送朋友一杯咖啡" |
| `get_order_status` | 订单状态查询 | "我的订单做好了吗" |

### 4.3 Resources（MCP 资源，LLM 可直接读取上下文）

```
starbucks://menu/seasonal        → 当季限定菜单（实时更新）
starbucks://stores/{city}        → 城市门店列表
starbucks://promotions/current   → 当前全国促销活动
starbucks://customization/guide  → 饮品定制选项说明
```

---

## 5. 与主流 CLI 的关系

### 5.1 定位关系

```
┌─────────────────────────────────────────────────────┐
│               AI Agent 运行层（MCP Client）          │
│                                                     │
│  Claude Code CLI  Cursor  Claude Desktop  自研 Agent │
│        └──────────────┴──────────┴──────────┘       │
│                   MCP Protocol                      │
└─────────────────────┬───────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   高德 MCP      星巴克 MCP     GitHub MCP
  (位置信息)     (点咖啡/门店)   (代码仓库)
```

**CLI 是 MCP Client，星巴克 MCP Server 是工具提供方**。CLI 不关心你是哪家的 MCP Server，只要符合协议，插上即用。

### 5.2 各主流 CLI 接入方式

**Claude Code CLI**（SITC 团队当前在用）

```bash
# ~/.claude/claude_code_settings.json
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/sse?key=xxx"
    }
  }
}

# 对话中直接使用
> 帮我查一下上海来福士附近的星巴克，今天有没有燕麦拿铁
# Claude Code 自动调用：search_nearby_stores → get_product_detail → check_store_inventory
```

**Cursor**

```json
// .cursor/mcp.json
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/mcp?key=xxx"
    }
  }
}
```

**Claude Desktop / 其他客户端**

| 客户端 | MCP 支持 | 典型场景 |
|---|---|---|
| Claude Code CLI | ✅ 原生 | Agent 任务中调工具，完整交易闭环 |
| Cursor | ✅ 原生 | IDE 内对话触发点单 |
| Claude Desktop | ✅ 原生 | 日常对话助手场景 |
| Cline / Roo Code | ✅ 原生 | VS Code 插件内使用 |
| 自研 Agent（LangChain 等） | ✅ MCP SDK | 企业内部自动化流程 |
| 微信 / 钉钉 AI 助手 | 🔜 跟进中 | 国内主流入口 |

### 5.3 完整交易场景示例

```
用户对 Claude Code 说：
"我要去陆家嘴开会，提前帮我在最近的星巴克下单
 一杯燕麦拿铁，大杯少冰，到店自取，用我的会员账号"

Claude Code 执行链：
  Step 1: search_nearby_stores(city="上海", landmark="陆家嘴")
          → 返回 3 家门店及距离
  Step 2: get_store_detail(store_id="SH-LJZ-001")
          → 确认营业中，支持自取
  Step 3: check_store_inventory(store_id="SH-LJZ-001", product="燕麦拿铁")
          → 确认有货
  Step 4: create_order(product="燕麦拿铁", size="venti", milk="oat",
                       ice="less", pickup_time="14:30")
          → 下单成功，取单号 #A042

返回用户：
"已在外滩来福士一楼门店（距陆家嘴步行 8 分钟）
 预约了一杯大杯燕麦拿铁少冰，取单号 #A042，
 预计 14:30 可取。"
```

---

## 6. 分阶段落地计划

### Phase 1：OpenAPI → MCP Wrapper（第 1–2 周）

**目标**：最小可用版本上线，验证技术可行性

**交付物**：
- MCP Adapter 服务（Node.js / TypeScript）
- 6 个只读 Tool 实现
- SSE Endpoint 可用
- 内部测试通过（Claude Code + Cursor）

**核心工作**：
- 搭建 MCP SDK 脚手架
- 逐一封装开放平台 REST API 为 MCP Tool
- 实现语义化转换层（JSON → 自然语言）
- API Key 透传鉴权

### Phase 2：托管部署 + Developer Console（第 3–5 周）

**目标**：生产级部署，开放外部开发者接入

**交付物**：
- 云函数部署（阿里云 FC / 腾讯云 SCF）
- API Gateway（鉴权、限流、监控）
- Developer Portal（申请 Key、查看用量）
- Streamable HTTP 支持
- 接入文档和 Quick Start Guide

### Phase 3：交易闭环 + Marketplace（第 6–8 周）

**目标**：支持完整点单流程，进入主流 MCP Marketplace

**交付物**：
- OAuth 2.0 授权 Flow（用户级会员绑定）
- 下单、礼品、会员 Tool 实现
- 提交 Claude MCP 目录 / Cursor 插件市场
- 监控告警体系

### 里程碑总览

```
Week 1-2:  [████████] Phase 1 完成 → 内部可用
Week 3-5:  [████████] Phase 2 完成 → 外部开发者可接入
Week 6-8:  [████████] Phase 3 完成 → 完整交易闭环上线
```

---

## 7. 技术实现细节

### 7.1 工程结构

```
starbucks-mcp-server/
├── src/
│   ├── server.ts              # MCP Server 入口
│   ├── tools/
│   │   ├── stores.ts          # 门店相关 Tools
│   │   ├── menu.ts            # 菜单相关 Tools
│   │   ├── inventory.ts       # 库存相关 Tools
│   │   └── orders.ts          # 下单相关 Tools（Phase 2）
│   ├── resources/
│   │   └── menu-resource.ts   # 菜单 Resource 定义
│   ├── adapters/
│   │   └── sbux-openapi.ts    # 开放平台 HTTP 客户端
│   └── formatters/
│       └── semantic.ts        # 语义化转换层
├── package.json
└── tsconfig.json
```

### 7.2 Tool 实现示例（门店搜索）

```typescript
// src/tools/stores.ts
server.tool(
  "search_nearby_stores",
  "搜索附近的星巴克门店，支持按城市、坐标、关键词查询",
  {
    latitude:  z.number().optional().describe("用户纬度"),
    longitude: z.number().optional().describe("用户经度"),
    city:      z.string().optional().describe("城市名，如'上海'"),
    keyword:   z.string().optional().describe("地标关键词，如'陆家嘴'"),
    radius:    z.number().default(3000).describe("搜索半径，单位米，默认3000"),
  },
  async (params, context) => {
    const apiKey = extractApiKey(context); // 从连接参数提取

    // 透传给开放平台
    const response = await fetch(
      `https://openapi.starbucks.com.cn/v1/stores/search`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(params)
      }
    );

    if (!response.ok) {
      throw new McpError(response.status, await response.text());
    }

    const raw = await response.json();

    // 语义化转换：JSON → 自然语言，让 LLM 更好理解
    return {
      content: [{
        type: "text",
        text: formatStoresForLLM(raw.stores)
      }]
    };
  }
);

// 语义化转换（核心设计，参考高德 MCP 最佳实践）
function formatStoresForLLM(stores: Store[]): string {
  if (!stores.length) return "附近暂无星巴克门店";

  return stores.map(s =>
    `**${s.name}**（${s.district}）\n` +
    `- 距您约 ${s.distance} 米，步行约 ${Math.ceil(s.distance / 80)} 分钟\n` +
    `- 营业时间：${s.openTime} - ${s.closeTime}\n` +
    `- 服务：${[
      s.hasSeating   ? '堂食' : '',
      s.drivethru    ? '得来速' : '',
      s.delivery     ? '外卖配送' : '',
      s.mobileOrder  ? '移动点单' : ''
    ].filter(Boolean).join('、')}\n` +
    `- 门店编号：${s.storeId}`
  ).join('\n\n');
}
```

### 7.3 API Key 提取逻辑

```typescript
// 兼容三种传递方式
function extractApiKey(context: ToolContext): string {
  // 方式1：URL param ?key=xxx
  const urlKey = context.connectionParams?.key;
  if (urlKey) return urlKey;

  // 方式2：HTTP Header Authorization: Bearer xxx
  const headerKey = context.headers?.authorization?.replace("Bearer ", "");
  if (headerKey) return headerKey;

  // 方式3：自定义 Header x-api-key: xxx
  const customKey = context.headers?.["x-api-key"];
  if (customKey) return customKey;

  throw new McpError(401, "Missing API Key");
}
```

### 7.4 错误处理

```typescript
// 开放平台错误码 → MCP 语义化错误
const ERROR_MAP: Record<number, string> = {
  401: "API Key 无效或已过期，请检查您的密钥",
  403: "当前 Key 无权限调用此接口",
  429: "请求频率超限，请稍后重试",
  503: "星巴克服务暂时不可用，请稍后重试",
};

function handleApiError(status: number, body: string): never {
  const message = ERROR_MAP[status] || `服务错误（${status}）`;
  throw new McpError(status, message);
}
```

---

## 8. 部署架构

### 8.1 云端托管（对标高德零运维模式）

```
外部 MCP Client
      │
      ▼
API Gateway（阿里云 APIG）
  - SSL 终止
  - API Key 提取传递
  - 限流（默认 100 QPS / Key）
  - 访问日志
      │
      ▼
函数计算 FC（无服务器）
  - Node.js 20 Runtime
  - 自动弹性伸缩
  - 多可用区部署
      │
      ▼
openapi.starbucks.com.cn（现有，不变）
```

### 8.2 Endpoint 规划

| Endpoint | 协议 | 说明 |
|---|---|---|
| `https://mcp.starbucks.com.cn/sse?key=xxx` | SSE | 当前主流，兼容性最好 |
| `https://mcp.starbucks.com.cn/mcp?key=xxx` | Streamable HTTP | 未来主流，2025 年新规范 |
| `https://mcp.starbucks.com.cn/health` | HTTP GET | 健康检查 |

### 8.3 监控指标

- Tool 调用成功率（目标 ≥ 99.5%）
- 语义转换 P95 延迟（目标 ≤ 500ms）
- 开放平台透传错误率
- 各 Tool 调用 Top N 统计

---

## 9. 资源与成本估算

### 9.1 人力投入

| 阶段 | 工作量 | 核心交付 |
|---|---|---|
| Phase 1 | 2人 × 2周 | MCP Adapter + 6个只读 Tool + SSE Endpoint |
| Phase 2 | 2人 × 3周 | 云部署 + Developer Portal + API Key 管理 |
| Phase 3 | 3人 × 3周 | OAuth 下单流 + Marketplace 注册 |
| **合计** | **约 16 人周** | **完整 MCP Server 上线** |

### 9.2 云资源成本（月度估算）

| 资源 | 规格 | 月费用估算 |
|---|---|---|
| 函数计算 FC | 按调用量计费 | ¥500–2000（视流量） |
| API Gateway | 标准版 | ¥300/月 |
| 日志服务 SLS | 按量 | ¥100–500 |
| **合计** | | **¥900–2800/月** |

---

## 10. 战略价值

### 10.1 与高德的本质差异

```
高德 MCP：AI Agent → 查询位置信息 → 返回数据
                         ↑
                    只有信息价值

星巴克 MCP：AI Agent → 查询 + 下单 + 支付 → 完成交易
                              ↑
                    信息价值 + 交易价值
```

**星巴克是少数可以在 MCP 上完成端到端交易闭环的品牌**，这是真正的护城河。

### 10.2 Agent Economy 中的位置

```
用户的 AI 个人助手（任意品牌）
         │
         │  "帮我在开会前订好咖啡"
         ▼
  AI Agent 自动规划 + 执行
         │
         ├── 高德 MCP → 查附近门店位置
         ├── 天气 MCP → 查今日天气
         └── 星巴克 MCP → 下单、支付、获取取单号
```

**星巴克不需要入侵任何 AI 平台**，只需要做好 MCP Server，所有 AI 助手天然都能调用。用户不需要打开 App，AI 助手就能帮他完成购买——这是从"主动打开 App"到"被动触达"的范式转变。

### 10.3 后续扩展方向

- **个性化推荐**：结合会员历史订单，MCP 返回个性化菜单推荐
- **多模态支持**：返回饮品图片 + 描述，提升 AI 助手的表达质量
- **生态合作**：与 AR 导航、智能音箱、车载助手打通
- **B 端延伸**：企业茶水间、会议室服务通过 MCP 自动补货下单

---

## 附录：快速验证步骤

Phase 1 上线后，用以下方式立即验证：

```bash
# 1. 安装 Claude Code CLI（如已安装跳过）
npm install -g @anthropic-ai/claude-code

# 2. 配置 Starbucks MCP
# 编辑 ~/.claude/claude_code_settings.json 添加：
{
  "mcpServers": {
    "starbucks": {
      "url": "https://mcp.starbucks.com.cn/sse?key=YOUR_KEY"
    }
  }
}

# 3. 验证 Tool 列表
claude mcp list

# 4. 对话验证
claude "帮我找上海静安区附近的星巴克，今天有没有燕麦拿铁"
```

---

*本文档由 SITC Digital Trading Team 维护，如有问题请联系 Sawyer Zhang*
