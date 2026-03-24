---
name: coffee-menu
description: 浏览Coffee Company菜单和饮品详情。当用户询问有什么喝的、菜单、饮品详情、热量营养等内容时使用。适用于"有什么新品"、"拿铁有哪些"、"这个多少卡"等请求。
allowed-tools: mcp__coffee-toc__nearby_stores, mcp__coffee-toc__browse_menu, mcp__coffee-toc__drink_detail, mcp__coffee-toc__nutrition_info
---

# 菜单浏览

帮助用户浏览 Coffee Company 菜单、查看饮品定制选项和营养信息。

## 工具选择

| 场景 | 工具 |
|------|------|
| 浏览完整菜单 | `browse_menu` (需先有 store_id) |
| 查看饮品定制选项 | `drink_detail` |
| 查询营养/热量信息 | `nutrition_info` |

注意：浏览菜单需要先选门店，如果用户未指定门店，先调用 `nearby_stores`。

饮品定制选项包括：杯型(中/大/超大)、奶类(全脂/燕麦/杏仁/豆/椰)、温度(热/冰)、甜度、加料。
