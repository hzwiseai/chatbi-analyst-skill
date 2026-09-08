"""Build a credential-free, self-contained skill ZIP from explicit sources."""

from pathlib import Path
import argparse
import json
import re
import zipfile


def read_version(skill_dir):
    """Skill 版本的唯一来源。平台要求每次上传都必须严格递增，
    所以版本不能写死在代码里——改这个文件即可，无需动打包逻辑。"""
    return (skill_dir / "VERSION").read_text().strip()


def workbuddy_frontmatter(content, version):
    """Add marketplace metadata to the exported Skill, preserving source format."""
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?=\r?\n|$)", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter")
    frontmatter = match.group(1)
    fields = {
        "version": version,
        "display_name": "慧言WiseBI分析Skill",
        "display_name_en": "WiseBI Analyst Skill",
        "description_zh": "通过 ChatBI MCP 查询获授权的业务数据，完成指标分析、趋势与异常诊断，并生成图表、指标卡和有数据依据的分析报告。",
        "description_en": "Query authorized business data through ChatBI MCP, analyze metrics, trends and anomalies, and generate charts, KPI cards and evidence-based reports.",
    }
    for key, value in fields.items():
        if not re.search(rf"^{key}:", frontmatter, re.MULTILINE):
            frontmatter += f"\n{key}: {json.dumps(value, ensure_ascii=False)}"
    return "---\n" + frontmatter + "\n---" + content[match.end():]


def build(output, *, workbuddy=False, version=None):
    root = Path(__file__).resolve().parent
    skill = root  # 独立仓库：Skill 文件即在仓库根目录
    version = version or read_version(skill)
    files = [(skill / "SKILL.md", "chatbi-analyst/SKILL.md")]
    files += [
        (skill / name, "chatbi-analyst/" + name)
        for name in ("README.md", ".env.example", ".gitignore")
    ]
    files += [
        (p, "chatbi-analyst/" + str(p.relative_to(skill)))
        for p in (skill / "references").glob("*.md")
    ]
    files += [
        (skill / "scripts/chatbi_client.py", "chatbi-analyst/scripts/chatbi_client.py")
    ]
    files.append(
        (skill / "scripts/render_chart.py", "chatbi-analyst/scripts/render_chart.py")
    )
    files += [
        (skill / "assets" / name, "chatbi-analyst/assets/" + name)
        for name in (
            "chart_viewer.html",
            "echarts.min.js",
            "ECHARTS-LICENSE",
            "ECHARTS-NOTICE",
        )
    ]
    files += [
        (p, "chatbi-analyst/scripts/chatbi_mcp/" + p.name)
        for p in (skill / "scripts/chatbi_mcp").glob("*.py")
    ]
    files.append(
        (skill / "scripts/requirements.txt", "chatbi-analyst/scripts/requirements.txt")
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, name in files:
            if not workbuddy:
                archive.write(source, name)
                continue
            # WorkBuddy accepts SKILL.md at ZIP root and one directory below it.
            name = str(Path(name).relative_to("chatbi-analyst"))
            if name == "SKILL.md":
                archive.writestr(name, workbuddy_frontmatter(source.read_text(), version))
                continue
            if name == "scripts/chatbi_mcp/__init__.py":
                continue
            replacements = {
                "scripts/chatbi_client.py": (
                    "scripts/chatbi_client.py",
                    "from chatbi_mcp.cli import main",
                    "from chatbi_cli import main",
                ),
                "scripts/chatbi_mcp/cli.py": (
                    "scripts/chatbi_cli.py",
                    "from .client import",
                    "from chatbi_transport import",
                ),
                "scripts/chatbi_mcp/client.py": (
                    "scripts/chatbi_transport.py",
                    "Path(__file__).resolve().parents[2]",
                    "Path(__file__).resolve().parents[1]",
                ),
            }
            if name in replacements:
                name, old, new = replacements[name]
                content = source.read_text()
                if content.count(old) != 1:
                    raise ValueError(f"Client layout changed; review WorkBuddy conversion: {source.name}")
                archive.writestr(name, content.replace(old, new))
            else:
                archive.write(source, name)
            if len(Path(name).parts) > 2:
                raise ValueError(f"WorkBuddy directory depth exceeded: {name}")
        # User-owned contents are local; publish only an empty workspace.
        archive.writestr("workspace/" if workbuddy else "chatbi-analyst/workspace/", "")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--workbuddy", action="store_true", help="Flatten ZIP to root + one directory level")
    parser.add_argument("--skill-version", help="Override the version in VERSION; must exceed the published one")
    args = parser.parse_args()
    print(build(args.output, workbuddy=args.workbuddy, version=args.skill_version))
