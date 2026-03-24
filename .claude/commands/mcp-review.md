# MCP Server Tool 设计审查

根据 MCP 接口设计准则（docs/MCP_API_DESIGN_GUIDE.md），审查指定 MCP Server 的工具定义。

## 审查准则（10 条）

- **C1 Description 三段式** — 做什么 + 什么时候用 + 触发短语
- **C2 极简参数** — 能推断的不要传
- **C3 参数扁平化** — 避免嵌套 object/array
- **C4 参数来源标注** — 参数说明写"从哪个 tool 获取"
- **C5 命名规范** — 前缀 + 一致风格 + 动词优先
- **C6 响应精简** — 裁剪到 LLM 所需最小字段集
- **C7 响应格式一致** — 错误格式统一、单位统一
- **C8 渐进式披露** — List 返回摘要 + ID，Detail 返回全量
- **C9 写操作安全** — 写前有预览确认，操作幂等
- **C10 敏感信息** — PII 脱敏

## 执行步骤

1. 定位目标文件：找到包含 `@mcp.tool()` 的 server 文件
2. 同时读取 formatter 和 mock_data 文件以了解响应格式
3. 逐个 tool 按 10 条准则审查
4. 输出每个 tool 的审查表格
5. 输出汇总：通过/建议优化/需修复数量 + Top 问题 + 具体修改建议

$ARGUMENTS
