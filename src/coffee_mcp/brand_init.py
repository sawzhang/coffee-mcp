"""Interactive brand initialization — generates brand.yaml from preset + Q&A.

Similar to `npm init` or `uv init`. Asks a few questions, picks a category
preset, and generates a complete brand.yaml ready to use.

Usage:
    uv run brand-init                    # interactive mode
    uv run brand-init --category tea     # skip category selection
    uv run brand-init --brand-id manner  # pre-fill brand ID
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import yaml

from .presets.catalog import PRESETS, get_preset, list_presets

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_BRANDS_DIR = _PROJECT_ROOT / "brands"


def _slugify(name: str) -> str:
    """Convert brand name to a safe directory name."""
    # Replace Chinese characters with pinyin-ish slug
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", slug)
    slug = slug.strip("_")
    return slug or "my_brand"


def _generate_instructions(brand_name: str, category_display: str) -> str:
    """Generate default MCP instructions for a brand."""
    return (
        f"{brand_name}消费者自助 MCP Server。\n"
        f"品类：{category_display}。\n"
        f"提供活动发现、优惠券领取、菜单浏览、门店查找、下单点餐等能力。\n"
        f"所有工具基于登录用户身份自动识别，无需传入会员ID。\n\n"
        f"安全说明：工具按风险分为 L0(公开只读) ~ L3(高危写入) 四级，\n"
        f"高危操作有频率限制和参数校验。\n\n"
        f"重要：下单前必须先调用 calculate_price 获取 confirmation_token，\n"
        f"然后将 confirmation_token 传入 create_order。"
    )


def _build_yaml(brand_id: str, brand_name: str, preset: dict,
                overrides: dict | None = None) -> dict:
    """Build complete brand.yaml dict from preset + overrides."""
    ov = overrides or {}
    category_display = preset["display_name"]

    # Auto-derive validation valid_* from option keys
    size_options = ov.get("size_options", preset["size_options"])
    milk_options = ov.get("milk_options", preset["milk_options"])
    temp_options = ov.get("temp_options", preset["temp_options"])
    extra_options = ov.get("extra_options", preset["extra_options"])

    validation = {**preset["validation"]}
    validation["phone_pattern"] = r"^1\d{10}$"
    validation["valid_sizes"] = list(size_options.keys())
    validation["valid_milks"] = list(milk_options.keys())
    validation["valid_temps"] = list(temp_options.keys())
    validation["valid_extras"] = list(extra_options.keys())
    validation["valid_pickup"] = ov.get("valid_pickup", ["自提", "外送", "堂食"])

    return {
        "brand_id": brand_id,
        "brand_name": brand_name,
        "server_name": f"{brand_name} ToC",
        "default_user_id": "CC_M_100001",
        "instructions": _generate_instructions(brand_name, category_display),
        "validation": validation,
        "rate_limits": ov.get("rate_limits", preset["rate_limits"]),
        "size_options": size_options,
        "milk_options": milk_options,
        "temp_options": temp_options,
        "sweetness_options": ov.get("sweetness_options", preset["sweetness_options"]),
        "extra_options": extra_options,
        "features": ov.get("features", preset["features"]),
    }


@click.command()
@click.option("--brand-id", default=None, help="Brand ID (directory name)")
@click.option("--category", default=None,
              type=click.Choice(list(PRESETS.keys())),
              help="Brand category preset")
@click.option("--non-interactive", is_flag=True, help="Skip prompts, use defaults")
def init(brand_id: str | None, category: str | None, non_interactive: bool):
    """Initialize a new brand configuration (interactive)."""
    click.echo()
    click.secho("  Coffee & Tea MCP Platform — Brand Init", fg="green", bold=True)
    click.secho("  ─────────────────────────────────────────", fg="green")
    click.echo()

    # Step 1: Brand name
    if non_interactive and not brand_id:
        brand_id = "my_brand"
    brand_name = click.prompt("  品牌名称", default="我的品牌") if not non_interactive else "My Brand"
    if not brand_id:
        suggested = _slugify(brand_name)
        brand_id = click.prompt("  品牌 ID (英文, 用于目录名)",
                                default=suggested) if not non_interactive else suggested

    # Check if already exists
    brand_dir = _BRANDS_DIR / brand_id
    if brand_dir.exists():
        if not non_interactive:
            if not click.confirm(f"  brands/{brand_id}/ 已存在，覆盖？", default=False):
                click.echo("  已取消。")
                return
        else:
            click.echo(f"  Warning: brands/{brand_id}/ already exists, overwriting.")

    # Step 2: Category selection
    if not category:
        click.echo()
        click.secho("  选择品类（决定默认菜单选项）：", bold=True)
        for i, info in enumerate(list_presets(), 1):
            click.echo(f"    {i}. {info['display_name']} — {info['description']}")
            click.echo(f"       例: {info['examples']}")

        if non_interactive:
            category = "coffee"
        else:
            choice = click.prompt("\n  选择", type=click.IntRange(1, len(PRESETS)), default=1)
            category = list(PRESETS.keys())[choice - 1]

    preset = get_preset(category)
    click.echo(f"\n  已选择: {preset['display_name']} 预设")

    # Step 3: Customization questions (only in interactive mode)
    overrides: dict = {}
    if not non_interactive:
        click.echo()
        click.secho("  定制选项（回车跳过使用默认值）：", bold=True)

        # Pickup types
        default_pickup = "自提, 外送, 堂食" if category != "tea" else "自提, 外送"
        pickup_input = click.prompt("  取餐方式 (逗号分隔)",
                                    default=default_pickup)
        overrides["valid_pickup"] = [p.strip() for p in pickup_input.split(",")]

        # Feature flags
        click.echo()
        click.secho("  功能开关：", bold=True)
        features = dict(preset["features"])
        for key, default in features.items():
            feature_names = {
                "campaigns": "活动日历", "coupons": "优惠券",
                "stars_mall": "积分商城", "delivery": "外送",
                "nutrition": "营养信息",
            }
            features[key] = click.confirm(
                f"    {feature_names.get(key, key)}", default=default)
        overrides["features"] = features

    # Step 4: Generate YAML
    config = _build_yaml(brand_id, brand_name, preset, overrides)

    # Step 5: Write files
    brand_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = brand_dir / "brand.yaml"

    yaml_content = (
        f"# {brand_name} — 自动生成 by brand-init\n"
        f"# 品类预设: {preset['display_name']}\n"
        f"# 修改此文件自定义品牌配置，参考 docs/BRAND_INTEGRATION_GUIDE.md\n\n"
    )
    yaml_content += yaml.dump(config, allow_unicode=True, default_flow_style=False,
                               sort_keys=False, width=120)

    yaml_path.write_text(yaml_content, encoding="utf-8")

    # Step 6: Verify
    click.echo()
    click.secho("  ✅ 品牌初始化完成！", fg="green", bold=True)
    click.echo()
    click.echo(f"  生成文件:")
    click.echo(f"    brands/{brand_id}/brand.yaml")
    click.echo()
    click.echo(f"  验证配置:")
    click.echo(f"    BRAND={brand_id} uv run coffee-company-toc")
    click.echo()
    click.echo(f"  下一步:")
    click.echo(f"    1. 编辑 brands/{brand_id}/brand.yaml 调整价格和选项")
    click.echo(f"    2. /brand-onboard 对接品牌后端 API")
    click.echo(f"    3. 或直接用 DemoAdapter 体验完整流程")
    click.echo()

    # Quick validation
    try:
        from .brand_config import load_brand_config, load_brand_adapter
        from .toc_server import create_toc_server
        cfg = load_brand_config(brand_id)
        adapter = load_brand_adapter(cfg)
        server = create_toc_server(cfg, adapter)
        tools = server._tool_manager.list_tools()
        click.secho(f"  验证通过: {cfg.brand_name} — {len(tools)} tools registered", fg="green")
    except Exception as e:
        click.secho(f"  ⚠️ 验证失败: {e}", fg="yellow")


if __name__ == "__main__":
    init()
