#!/usr/bin/env python3
"""学者网通用栏目 → 飞书日历 同步脚本。

自动登录学者网，抓取指定栏目（如"我的动态""我的课程"）中包含日期信息的内容，
映射为飞书日历事件并同步写入，通过本地状态文件去重。

用法：
    python sync_general.py --per-section-limit 10  # 每个栏目最多同步 10 条
    python sync_general.py --dry-run               # 预览，不写入飞书

依赖：pip install requests beautifulsoup4 python-dotenv（另需系统安装 Node.js）
"""

import argparse
import time

import requests

from scholat_sync.auth import login_scholat
from scholat_sync.config import SCHOLAT_HOME_URL, STATE_FILE, TIMEZONE
from scholat_sync.feishu import create_event, ensure_calendar, get_tenant_access_token
from scholat_sync.scraper import (
    extract_section_links,
    fingerprint,
    load_state,
    save_state,
    scrape_schedule_items,
)


def sync(dry_run: bool, per_section_limit: int) -> None:
    """执行完整同步流程。"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    })

    print("[INFO] 登录学者网...")
    login_scholat(session)
    print("[INFO] 学者网登录成功")

    home_resp = session.get(SCHOLAT_HOME_URL, timeout=30)
    home_resp.raise_for_status()

    section_links = extract_section_links(home_resp.text)
    if not section_links:
        print("[WARN] 在首页未找到指定栏目链接，将直接扫描首页")
        section_links = [("首页", SCHOLAT_HOME_URL)]

    all_items = []
    for section, url in section_links:
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            items = scrape_schedule_items(section, url, resp.text, per_section_limit)
            print(f"[INFO] 栏目 {section} 抓取到 {len(items)} 条可识别日程")
            all_items.extend(items)
        except Exception as exc:
            print(f"[WARN] 栏目抓取失败 {section}: {exc}")

    if not all_items:
        print("[WARN] 未识别到包含日期的条目。可检查目标页面是否包含日期文本。")
        return

    state = load_state(STATE_FILE)
    existing = set(state.get("fingerprints", []))
    new_items = [item for item in all_items if fingerprint(item) not in existing]

    print(f"[INFO] 共识别 {len(all_items)} 条，新增 {len(new_items)} 条")
    if not new_items:
        return

    if dry_run:
        for item in new_items:
            print(f"[DRY-RUN] {item.start_dt.strftime('%Y-%m-%d %H:%M')} | {item.source_section} | {item.title}")
        return

    token = get_tenant_access_token()
    calendar_id = ensure_calendar(token)

    created = 0
    for item in new_items:
        try:
            create_event(
                token, calendar_id,
                summary=f"[{item.source_section}] {item.title}",
                description=(
                    f"来源栏目: {item.source_section}\n"
                    f"来源链接: {item.source_url}\n"
                    f"原文: {item.text}"
                ),
                start_ts=int(item.start_dt.timestamp()),
                end_ts=int(item.end_dt.timestamp()),
            )
            created += 1
            existing.add(fingerprint(item))
            print(f"[SYNCED] {item.start_dt.strftime('%Y-%m-%d %H:%M')} | {item.source_section} | {item.title}")
            time.sleep(0.2)
        except Exception as exc:
            print(f"[ERROR] 同步失败: {item.title} - {exc}")

    state["fingerprints"] = sorted(existing)
    save_state(STATE_FILE, state)
    print(f"[DONE] 本次创建飞书日程 {created} 条")


def main() -> None:
    parser = argparse.ArgumentParser(description="学者网通用栏目同步到飞书日历")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取解析，不写入飞书")
    parser.add_argument("--per-section-limit", type=int, default=20, help="每个栏目最多抓取条目数")
    args = parser.parse_args()

    sync(dry_run=args.dry_run, per_section_limit=args.per_section_limit)


if __name__ == "__main__":
    main()
