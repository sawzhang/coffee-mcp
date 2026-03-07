# 部署架构决策：独立 Adapter vs 改造现有平台

## 先定义两个方案

### 方案 A：独立 MCP Adapter 服务

```
B2B Agent ──MCP──▶ mcp.starbucks.com.cn (新服务)
                         │
                    HTTPS + HMAC 签名
                         │
                         ▼
                   openapi.starbucks.com.cn (不动)
```

MCP Adapter 是一个**独立进程/独立服务**，自己实现 HMAC 签名逻辑，
通过公网/内网调用现有 HTTP 开放平台。

### 方案 B：在现有开放平台内部加 MCP 协议

```
B2B Agent ──MCP──▶ openapi.starbucks.com.cn/mcp (同一服务新路由)
                         │
                    进程内直接调用
                         │
                         ▼
                   现有业务 Handler (不动)
```

在现有 HTTP 开放平台的 API Gateway 或应用层，新增 MCP 协议端点，
直接复用同进程的鉴权中间件和路由逻辑。

---

## 逐项对比

### 1. 鉴权复用

| | 方案 A（独立服务） | 方案 B（改造平台） |
|---|---|---|
| HMAC 签名 | Adapter 必须**重新实现**一套签名逻辑，构造 X-Date/Digest/Authorization | 直接复用现有网关的鉴权中间件，**零重复代码** |
| IP 白名单 | Adapter 的出口 IP 需加入白名单，或走内网绕过 | 天然在网关内部，白名单对 Adapter 无意义 |
| 接口授权清单 | Adapter 用自己的 appKey 调开放平台，权限是 Adapter 的而不是 B2B 客户的 | 直接拿到 B2B 客户原始 appKey，**权限粒度与 HTTP 完全一致** |
| 限流 | 两层限流：MCP 层一次 + 开放平台一次 | 一层限流，复用现有策略 |

**关键问题**：方案 A 的 Adapter 用谁的 appKey 调开放平台？

```
选项 1：用 Adapter 自己的超级 appKey
  → 所有 B2B 客户的请求都走同一个 Key
  → 丧失了每客户独立的权限隔离、限流、审计
  → 本质上 Adapter 变成了一个"代理人"，安全降级

选项 2：B2B 客户传 appKey+appSecret 给 Adapter，Adapter 代签
  → Adapter 拿到了客户的 Secret，成为安全单点
  → 客户 Secret 在 Adapter 内存中，泄露面扩大
  → 且 Adapter 需要完整重实现签名逻辑

选项 3：B2B 客户自己签好，Adapter 透传
  → 客户 Agent 需要实现 HMAC 签名 + MCP 协议
  → 接入门槛比直接调 HTTP 还高，MCP 失去意义
```

**结论：方案 A 的鉴权链路怎么设计都会引入额外的安全复杂度或能力退化。**

---

### 2. 网络与性能

| | 方案 A | 方案 B |
|---|---|---|
| 网络跳数 | Agent → Adapter → Gateway → 后端 (**3 跳**) | Agent → Gateway+MCP → 后端 (**2 跳**) |
| 额外延迟 | 多一次 HTTPS 往返 (~10-50ms 内网, ~50-200ms 公网) | 进程内调用，无额外延迟 |
| SSE 长连接 | Adapter 持有 SSE 连接 + 每次 Tool 调用发起新 HTTP | Gateway 直接持有 SSE，Tool 调用走进程内 |
| 运维 | 两个服务要分别部署、监控、扩容 | 一个服务统一运维 |

---

### 3. Tool 注册与接口同步

| | 方案 A | 方案 B |
|---|---|---|
| 新增 HTTP 接口 | 开放平台加完接口后，Adapter 要**同步新增** Tool 定义、参数映射、语义化模板 | 在同一代码库中加一个 Tool 注册 + formatter，**一次提交** |
| 参数定义 | Adapter 按文档手写参数 Schema，可能与实际不一致 | 可以直接从现有接口的 Swagger 定义**自动生成** Tool Schema |
| 版本同步风险 | 开放平台改了字段，Adapter 不知道 → 运行时报错 | 同代码库，编译期就能发现 |

---

### 4. 技术栈适配

| | 方案 A | 方案 B |
|---|---|---|
| 语言选择 | 自由选（Python/TypeScript/Go 都有 MCP SDK） | 受限于现有平台技术栈（大概率 Java/Spring） |
| MCP SDK 成熟度 | Python/TS SDK 最成熟 | Java MCP SDK 相对较新（Spring AI MCP 2025 年发布） |
| 团队技能 | 可以用最熟悉的语言 | 需要 Java 团队学习 MCP 协议 |

---

### 5. 风险与演进

| | 方案 A | 方案 B |
|---|---|---|
| 对现有平台的风险 | **零风险**，完全不碰现有代码 | 需要在生产代码中加新模块，有回归风险 |
| MCP 协议变更 | Adapter 独立升级，不影响 HTTP 平台 | 需要在平台代码中跟进协议变更 |
| 渐进式上线 | 灰度简单，Adapter 可以只对部分客户开放 | 需要在 Gateway 层做灰度路由 |
| 回滚 | 下掉 Adapter 服务即可，HTTP 平台完全不受影响 | 需要从平台代码中回滚 MCP 模块 |

---

## 深层分析：MCP 层到底做了什么

把 MCP Adapter 做的事情拆开看：

```
┌──────────────────────────────────────────────────┐
│              MCP Adapter 的三个职责                │
│                                                  │
│  ① MCP 协议处理                                   │
│     SSE/Streamable HTTP 连接管理                  │
│     Tool 注册、参数解析、结果封装                   │
│     → 纯协议层，与业务无关                         │
│                                                  │
│  ② 鉴权适配                                       │
│     从 MCP 连接提取凭证                            │
│     构造 HMAC/SM2 签名                            │
│     → 本质上是重新实现开放平台网关的一部分功能       │
│                                                  │
│  ③ 语义化转换                                      │
│     JSON 响应 → 自然语言                           │
│     错误码 → 友好提示                              │
│     → 核心增量价值，无论哪个方案都需要              │
│                                                  │
└──────────────────────────────────────────────────┘
```

方案 A 需要实现 ①②③；方案 B 只需要实现 ①③，② 已经有了。

**② 是最大的分水岭**：如果独立服务，签名逻辑要外部重写一遍；
如果在平台内部，签名直接复用。

---

## 推荐：方案 B 的变体 —— "内部独立模块"

既不是完全独立的服务，也不是侵入式改造现有路由，
而是在现有开放平台**内部新增一个 MCP 模块**，以插件化方式挂载：

```
┌─────────────────────────────────────────────────────────────┐
│                  openapi.starbucks.com.cn                     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    API Gateway                         │ │
│  │                                                        │ │
│  │   /crmadapter/*  ──┐                                   │ │
│  │   /coupon/*     ──┤   现有 HTTP 路由（不动）             │ │
│  │   /cashier/*    ──┤   ↓                                │ │
│  │   /equity/*     ──┘   现有 Handler + HMAC 鉴权          │ │
│  │                                                        │ │
│  │   /mcp          ──┐   新增 MCP 路由                     │ │
│  │   /sse          ──┤   ↓                                │ │
│  │                    │                                    │ │
│  └────────────────────┼────────────────────────────────────┘ │
│                       ▼                                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              MCP Module（新增，独立包）                   │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ MCP Protocol │  │ Tool Registry│  │ Semantic      │ │ │
│  │  │ Handler      │  │ (40 Tools)   │  │ Formatter     │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │ │
│  │         │                 │                  │         │ │
│  │         └─────── 进程内调用 ─────────────────┘         │ │
│  │                          │                             │ │
│  │                          ▼                             │ │
│  │              复用现有 Handler + 鉴权中间件               │ │
│  │              （不重写，直接 import 调用）                 │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 这个方案的关键设计

**1. MCP 模块是一个独立的 Maven Module / 子包**

```
openapi-platform/
├── gateway/                  # 现有网关（不动）
├── services/                 # 现有业务服务（不动）
│   ├── member-service/
│   ├── coupon-service/
│   └── ...
├── mcp-module/               # 新增（独立模块）
│   ├── McpEndpoint.java      # SSE/Streamable HTTP 端点
│   ├── ToolRegistry.java     # Tool 注册表（自动从 Swagger 生成）
│   ├── SemanticFormatter.java# 语义化转换
│   └── McpAuthFilter.java    # 从 MCP 连接头提取凭证，注入到现有鉴权链
└── pom.xml                   # mcp-module 作为可选依赖引入
```

**2. 鉴权：零重写，注入到现有链路**

```java
// McpAuthFilter：不重写签名，而是把 MCP 连接头映射到现有 HTTP 请求头
// 让现有的 HmacAuthFilter 来做真正的验签

public class McpAuthFilter {
    // MCP SSE 建连时，从连接头提取 appKey
    // 每次 Tool 调用时，构造一个内部 HttpServletRequest
    // 填入 X-Date / Digest / Authorization
    // 交给现有 HmacAuthFilter 处理
    // → 如果现有平台已经有签名工具类，直接复用
}
```

**3. Tool 注册：从 Swagger 自动生成**

现有平台声明了 Swagger 2.0 规范，可以自动化：

```
Swagger JSON → 遍历所有 API Path → 生成 MCP Tool 定义
  - Tool name: 路径转下划线 (如 /coupon/detail → coupon_detail)
  - Description: Swagger 中的 summary
  - Parameters: Swagger 中的 request body schema
  - 只需人工补充语义化 Formatter
```

**4. 部署：同进程但可独立开关**

```yaml
# application.yml
mcp:
  enabled: true              # 开关，关掉就回到纯 HTTP 模式
  endpoint: /mcp             # MCP Streamable HTTP 端点
  sse-endpoint: /sse         # SSE 端点
  tools:
    phase: 1                 # 只开放 Phase 1 的只读 Tools
```

---

## 决策矩阵

| 维度 | 方案 A（独立服务） | 方案 B（内部模块） | 权重 |
|------|-------------------|-------------------|------|
| 鉴权复用 | 需重写签名 | 直接复用 | **高** |
| 安全性 | Secret 暴露面大 | Secret 不出进程 | **高** |
| 权限隔离 | 退化或复杂 | 与 HTTP 完全一致 | **高** |
| 对现有平台风险 | 零 | 低（独立模块可关闭） | 中 |
| 上线速度 | 快（不碰现有代码） | 中（需要现有团队配合） | 中 |
| 运维成本 | 两个服务 | 一个服务 | 中 |
| 接口同步成本 | 高（手动同步） | 低（同代码库） | 中 |
| 技术栈灵活性 | 高（Python/TS） | 低（受限 Java） | 低 |
| MCP 协议演进 | 快速跟进 | 跟进速度受平台发版节奏影响 | 低 |

---

## 最终建议

**推荐方案 B（内部独立模块），理由的优先级：**

1. **鉴权是核心** —— 开放平台的鉴权体系（HMAC 签名 + IP 白名单 + 接口授权 + 限流）是多年积累的安全基座，独立服务无论怎么设计都要在这套体系外面再套一层或重写一遍，安全和权限隔离都会打折扣

2. **权限粒度不能丢** —— 每个 B2B 客户有独立的 appKey、独立的接口授权清单、独立的 IP 白名单。内部模块天然继承这些，独立服务要么丢失（用超级 Key），要么增加安全风险（代管客户 Secret）

3. **独立模块 ≠ 侵入改造** —— 作为一个可选的 Maven Module 引入，有开关控制，不动现有任何路由和 Handler。回滚就是把开关关掉

4. **语义化才是真正的增量** —— 无论哪个方案，语义化转换层（JSON → 自然语言）都要写。方案 B 只需要写这一层，方案 A 还要额外重写鉴权

**唯一选方案 A 的场景**：现有平台团队完全没有带宽或意愿配合，且 MCP 需要在极短时间内上线做 PoC。这时独立服务可以作为**过渡方案**，但中期仍应回归方案 B。
