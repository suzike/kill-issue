#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汽车软件问题排查 skill（Kill-Issue）—— 初始化脚本

一键创建排查项目所需的目录结构、台账与问题文件夹：

    python init_context.py <项目根> [--context-dir 000-context] [--issue "001-标题"] [--organize <目录>]

功能：
  1. 创建通用上下文目录（000-context/01_Model ... 07_Logs）。已存在的目录不重建，只报告。
  2. 创建问题清单台账（项目根 问题清单.md），已存在则跳过。
  3. --issue "001-标题"：额外创建问题文件夹，内部按三级分级：
       001/  —— 问题描述与排查上下文（问题描述.md + logs/）
       002/  —— 中间排查过程数据（脚本、中间结果）
       003/  —— 最终调查报告与证据
  4. --organize <目录>：对散放文件做启发式归类到 000-context 子目录（*.slx→01_Model、
     *_autosar_rtw/*.c/*.h→02_Code、需求文档→03_Requirement、接口/ARXML/DBC→04_Interface、
     *.sldd/*.a2l→05_Calibration、测试说明→06_Test、日志/报文→07_Logs）；
     不确定类别的文件列出但不移动。

已有工程（如 ModelandCode_SOP_3/）本身可作为通用上下文，排查前按 SKILL.md 第 0 步
将其改名/归类为 000-context；脚本会识别已存在目录，不会重复创建。
"""

import argparse
import os
import shutil
import sys

# 上下文目录：编号 - 名称 - 用途说明
CONTEXT_DIRS = [
    ("01_Model", "Simulink 控制模型 (*.slx / 子系统 xml)"),
    ("02_Code", "模型生成的代码包 (*_autosar_rtw/ 等)"),
    ("03_Requirement", "需求文档 (SRS / 功能规范 / 变更单)"),
    ("04_Interface", "接口信号表 / ARXML / DBC"),
    ("05_Calibration", "标定文件 (*.sldd / *.a2l / 标定表)"),
    ("06_Test", "测试环境说明 (HIL/MIL 配置、5S/6S 机制等)"),
    ("07_Logs", "共享日志/报文 (可选)"),
]

# --organize 启发式规则：关键字/扩展名 -> 目标子目录（按优先级从上到下）
ORGANIZE_RULES = [    (("01_Model",), (".slx",), ()),
    (("02_Code",), (".c", ".h", ".cpp", ".hpp"), ()),
    (("02_Code",), (), ("autosar_rtw", "ert_rtw", "generated_code")),
    (("04_Interface",), (".dbc", ".arxml", ".xml"), ()),
    (("04_Interface",), (), ("接口", "interface", "rte_io", "dbc", "arxml", "signal")),
    (("05_Calibration",), (".sldd", ".a2l", ".cals"), ()),
    (("03_Requirement",), (".docx", ".doc", ".pdf"), ()),
    (("03_Requirement",), (), ("需求", "srs", "spec", "规范", "变更", "requirement")),
    (("05_Calibration",), (), ("标定", "cal", "a2l", "sldd")),
    (("06_Test",), (), ("hil", "mil", "测试", "test", "台架")),
    (("07_Logs",), (".mat", ".csv", ".asc", ".blf", ".mdf", ".mf4", ".log", ".txt"), ()),
]

# 模板目录：脚本同级 ../../assets/issue-folder-template/（与 skill 打包结构对应）
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "issue-folder-template")

ISSUE_TEMPLATE = """# 问题描述（由排查 agent 自动补全，工程师无需填写）

> 本文件由排查流程自动生成/更新：agent 从工程师提供的输入中提取信息，缺失项通过澄清提问补齐。
> 工程师只需提供：问题文件（logs / CANoe·CANape 报文 / 截图 / trace）+ 输入框里的一句话描述，其余由 agent 完成。

## 问题

{title}

## 现象与预期

- 实际行为：（自动提取，引用附件证据；无法确定时标记"待确认"）
- 预期行为：（自动提取；无法确定时标记"待确认"）

## 复现条件

- 工况（模式、温度、车速、配置 5S/6S 等）：（从输入提取或澄清）
- 复现步骤：（如有）
- 是否必现：（必现 / 偶发；未知标记"待确认"）

## 环境与版本

- 测试环境（HIL / MIL / 台架 / 整车）：
- 软件版本 / 构建时间：
- 模型版本：
- 标定版本：

## 文件清单（工程师放入 001/ 或拖入对话的文件）

| 文件名 | 类型 | 用途 / 时间段 |
|---|---|---|
| （自动登记） | | |

## 变更背景

- （是否新引入、之前是否正常、最近改了什么；未知标记"待确认"）
"""

LEDGER_HEADER = """# 问题清单（台账）

| 编号 | 标题 | 状态 | 归属层 | 结论一句话 | 报告文件 |
|---|---|---|---|---|---|
"""


def create_context_dir(root: str, name: str) -> None:
    """创建上下文目录树，报告新建/存在。"""
    base = os.path.join(root, name)
    for sub, note in CONTEXT_DIRS:
        path = os.path.join(base, sub)
        if os.path.isdir(path):
            print(f"  [存在] {path}")
        else:
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, "说明.txt"), "w", encoding="utf-8") as f:
                f.write(f"{sub}：{note}\n")
            print(f"  [新建] {path}（{note}）")


def create_ledger(root: str) -> None:
    """创建问题清单台账（已存在则跳过）。"""
    path = os.path.join(root, "问题清单.md")
    if os.path.isfile(path):
        print(f"  [存在] {path}")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(LEDGER_HEADER)
    print(f"  [新建] {path}")


def create_issue(root: str, issue: str) -> None:
    """创建问题文件夹（001/002/003 三级）：
    - 001/：问题描述与排查上下文（问题描述.md + logs/ + 附件说明.md）
    - 002/：中间排查过程数据（脚本、中间结果）
    - 003/：最终调查报告与证据
    模板从 assets/issue-folder-template/ 读取（assets 缺失时用内嵌模板兜底）。"""
    folder = os.path.join(root, issue)
    if os.path.isdir(folder):
        print(f"  [存在] {folder}（跳过）")
        return
    for sub in ("001", "002", "003"):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
        print(f"  [新建] {folder}/{sub}/")
    logs = os.path.join(folder, "001", "logs")
    os.makedirs(logs, exist_ok=True)
    desc = os.path.join(folder, "001", "问题描述.md")
    if not os.path.isfile(desc):
        tmpl = _read_asset("问题描述.md") or ISSUE_TEMPLATE
        content = tmpl.format(title=issue) if "{title}" in tmpl \
            else tmpl.replace("<自动提取的一句话现象描述>", issue)
        with open(desc, "w", encoding="utf-8") as f:
            f.write(content)
    attach = os.path.join(logs, "附件说明.md")
    if not os.path.isfile(attach):
        note = _read_asset("附件说明.md")
        if note is not None:
            with open(attach, "w", encoding="utf-8") as f:
                f.write(note)
    print(f"  [新建] {folder}/001/问题描述.md + 001/logs/（本问题专属上下文）")


def _read_asset(name: str) -> str | None:
    """从 assets/issue-folder-template/ 读取模板文件；不存在返回 None。"""
    path = os.path.join(ASSETS_DIR, name)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None


def guess_category(name: str, is_dir: bool) -> str | None:
    """按启发式规则判断类别，返回目标子目录名；不确定返回 None。"""
    lower = name.lower()
    ext = os.path.splitext(name)[1].lower()
    for targets, exts, keywords in ORGANIZE_RULES:
        if exts and ext in exts:
            return targets[0]
        if keywords and any(k in lower for k in keywords):
            return targets[0]
    # 代码包目录：目录名含 autosar_rtw/ert_rtw 等
    if is_dir and any(k in lower for k in ("autosar_rtw", "ert_rtw", "generated_code")):
        return "02_Code"
    return None


def organize(root: str, context_name: str, src: str) -> None:
    """把 src 目录下的散放条目启发式归类到上下文子目录。"""
    src = os.path.abspath(src)
    base = os.path.join(os.path.abspath(root), context_name)
    if not os.path.isdir(src):
        print(f"错误：待归类目录不存在 {src}")
        return
    moved, unknown = [], []
    for entry in sorted(os.listdir(src)):
        path = os.path.join(src, entry)
        cat = guess_category(entry, os.path.isdir(path))
        if cat is None:
            unknown.append(entry)
            continue
        dst = os.path.join(base, cat, entry)
        if os.path.exists(dst):
            unknown.append(f"{entry}（目标已存在，未移动）")
            continue
        shutil.move(path, dst)
        moved.append(f"{entry} -> {context_name}/{cat}/")
    print("  [归类完成]")
    for m in moved:
        print(f"    {m}")
    if unknown:
        print("  [不确定类别，请人工决定]")
        for u in unknown:
            print(f"    {u}")


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化汽车软件问题排查项目结构")
    parser.add_argument("project_root", help="项目根目录")
    parser.add_argument("--context-dir", default="000-context",
                        help="通用上下文目录名（默认 000-context）")
    parser.add_argument("--issue", help='创建问题文件夹，如 "001-标题"')
    parser.add_argument("--organize", metavar="DIR",
                        help="对指定目录下的散放文件做启发式归类到上下文子目录")
    args = parser.parse_args()

    root = args.project_root
    if not os.path.isdir(root):
        print(f"错误：目录不存在 {root}")
        return 1

    if args.organize:
        print(f"[归类] {args.organize} -> {args.context_dir}/")
        create_context_dir(root, args.context_dir)  # 确保目标子目录存在
        organize(root, args.context_dir, args.organize)
        return 0

    print(f"[1/3] 通用上下文目录 {args.context_dir}/")
    create_context_dir(root, args.context_dir)

    print("[2/3] 问题清单台账")
    create_ledger(root)

    if args.issue:
        print(f"[3/3] 问题文件夹 {args.issue}/")
        create_issue(root, args.issue)
    else:
        print("[3/3] 跳过（未指定 --issue，可用 --issue \"001-标题\" 创建问题文件夹）")

    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
