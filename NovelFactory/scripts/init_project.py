# -*- coding: utf-8 -*-
"""初始化写作工作区 novel_factory/：生成 config.toml、world.md、人物模板、大纲占位、记忆文件。幂等，不覆盖已有文件。"""
from __future__ import annotations

from pathlib import Path

from ..core.utils import save_text

CONFIG_TPL = """# NovelFactory 写作工作区配置
[novel]
title = "待填写书名"
genre = "待填写题材"
chapter_word_count = 2000
word_tolerance = 0.1
tone = "网文通俗叙事，少AI腔，多用场景动作对话推进"

[llm]
# provider: ollama（本地默认） | openai（OpenAI兼容接口）
provider = "ollama"
base_url = "http://localhost:11434"
model = "qwen3.5:9b"
temperature_write = 0.7
temperature_review = 0.2
timeout = 300

[pipeline]
start = 1
end = 5
max_retry = 1
"""

WORLD_TPL = """# 世界观
## 世界背景
【填写世界基础背景：时代、地域、人文】

## 力量体系/境界
【境界、修炼规则、能力限制，务必写清上限与代价】

## 势力分布
各大宗门/家族/组织：名称、立场、彼此矛盾

## 通用规则
世界底层硬性规则（不可随意改动），例如能量守恒、规则类限制

## 禁忌与风险
【不要写的题材 / 平台风控注意项，供各 Agent 遵守】
"""

CHARACTER_TPL = """# {name} 档案
- 姓名：
- 年龄：
- 外貌：
- 性格：
- 过往经历：
- 能力/金手指：
- 目标与执念：
- 弱点：
- 与其他人物关系：
- 当前状态：【每次剧情变化，由记忆Agent更新】
"""


def init_workspace(workspace: str | Path, force: bool = False) -> Path:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)

    def write_if_missing(rel: str, content: str) -> bool:
        p = ws / rel
        if p.exists() and not force:
            return False
        save_text(p, content)
        return True

    (ws / "characters").mkdir(parents=True, exist_ok=True)
    (ws / "plot" / "chapter_plans").mkdir(parents=True, exist_ok=True)
    (ws / "manuscript").mkdir(parents=True, exist_ok=True)
    (ws / "memory").mkdir(parents=True, exist_ok=True)

    write_if_missing("config.toml", CONFIG_TPL)
    write_if_missing("world.md", WORLD_TPL)
    write_if_missing("characters/hero.md", CHARACTER_TPL.format(name="主角"))
    write_if_missing("characters/villain.md", CHARACTER_TPL.format(name="反派"))
    write_if_missing("plot/full_outline.md", "# 全书总大纲\n\n## 核心冲突\n【一句话主线冲突】\n\n## 起承转合\n【开端/发展/高潮/结局方向】\n\n## 三大转折点\n1. 【待规划】\n2. 【待规划】\n3. 【待规划】\n\n## 结局方向\n【待规划】\n")
    write_if_missing("plot/volume1.md", "# 第一卷大纲\n\n## 本卷目标\n【本卷要达成的剧情目标】\n\n## 主要冲突\n【冲突与对手】\n\n## 登场新人物\n- 【待规划】\n\n## 本卷高潮\n【高潮场面】\n\n## 卷收尾钩子\n【引出下一卷的悬念】\n")
    write_if_missing("memory/timeline.md", "# 时间线（由记忆Agent自动追加）\n")
    write_if_missing("memory/foreshadow.md", "# 伏笔清单（标记【未回收】/【已回收】）\n")
    return ws


if __name__ == "__main__":
    from pathlib import Path as _P
    init_workspace(_P(__file__).resolve().parent.parent.parent / "novel_factory")
    print("✅ novel_factory 工作区初始化完成")
