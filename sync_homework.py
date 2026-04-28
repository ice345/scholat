#!/usr/bin/env python3
"""学者网作业 → 飞书日历 同步脚本（日常使用）。

用法：
    python sync_homework.py --limit 5          # 创建最多 5 条作业日程
    python sync_homework.py --dry-run --limit 5 # 预览，不写入飞书
    python sync_homework.py --force                # 忽略去重，重新创建

依赖：pip install requests beautifulsoup4 python-dotenv（另需系统安装 Node.js）
"""

import argparse
import time
from datetime import datetime, timedelta

import requests
from requests.exceptions import ProxyError, RequestException

from scholat_sync.auth import login_scholat
from scholat_sync.config import FEISHU_CALENDAR_ID, HOMEWORK_URL
from scholat_sync.feishu import (
    create_event,
    get_tenant_access_token,
    update_event,
)
from scholat_sync.homework import (
    fingerprint,
    load_state,
    parse_homework_page,
    save_state,
    sort_by_deadline,
)


def resolve_calendar_id(cli_calendar_id: str) -> str:
    """解析目标日历 ID（优先级：CLI > .env CALENDAR_ID）。"""
    cid = cli_calendar_id.strip() or FEISHU_CALENDAR_ID
    if not cid:
        raise RuntimeError(
            "未提供目标日历 ID。请在 .env 设置 CALENDAR_ID 或通过 --calendar-id 传入。"
        )
    return cid


def sync(args) -> None:
    """执行作业同步。

    流程：登录 → 抓取作业 → 排序 → 去重/更新 → 写入飞书。
    """
    # ── 登录学者网 ──
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    })
    session.trust_env = False

    print("[INFO] 登录学者网...")
    max_retries = 2
    for attempt in range(max_retries):
        try:
            login_scholat(session)
            break
        except ProxyError:
            if attempt < max_retries - 1:
                print("[WARN] 代理连接异常，重试中...")
            else:
                raise RuntimeError("登录失败：多次代理连接异常，请检查网络")
        except RequestException as exc:
            raise RuntimeError(f"登录请求失败: {exc}")
    print("[INFO] 登录成功")

    # ── 抓取作业列表 ──
    try:
        resp = session.get(args.url, timeout=30)
        resp.raise_for_status()
    except RequestException as exc:
        raise RuntimeError(f"获取作业页失败: {exc}")

    homeworks = parse_homework_page(resp.text, args.url)
    if not homeworks:
        print("[WARN] 未识别到作业数据，请检查页面结构是否变化")
        return

    homeworks = sort_by_deadline(homeworks)
    print(f"[INFO] 识别到作业 {len(homeworks)} 条")

    # 过滤掉没有截止时间的作业
    with_deadline = [hw for hw in homeworks if hw.deadline_date is not None]
    no_deadline_count = len(homeworks) - len(with_deadline)
    if no_deadline_count > 0:
        print(f"[INFO] 其中 {no_deadline_count} 条无截止时间，本次跳过")
    if not with_deadline:
        print("[WARN] 所有作业均无截止时间，无法创建日历事件")
        return

    selected = with_deadline[:args.limit]
    print(f"[INFO] 待同步 (前 {len(selected)} 条，按截止时间排序):")
    for i, hw in enumerate(selected, 1):
        deadline_str = hw.deadline_date.strftime("%Y-%m-%d %H:%M") if hw.deadline_date else "无"
        print(f"  [{i}] {hw.title} | 截止: {deadline_str} | 状态: {hw.status}")

    if args.dry_run:
        return

    # ── 去重 / 更新判断 ──
    state = load_state()
    existing_items = state.get("items", {})

    token = get_tenant_access_token()
    calendar_id = resolve_calendar_id(args.calendar_id)
    print(f"[INFO] 目标日历: {calendar_id}")

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for hw in selected:
        fp = fingerprint(hw)
        deadline_ts = int(hw.deadline_date.timestamp())
        end_ts = int((hw.deadline_date + timedelta(hours=1)).timestamp())

        summary = f"[作业] {hw.title}"
        description = (
            f"状态: {hw.status}\n"
            f"发布人: {hw.publisher}\n"
            f"截止时间: {hw.deadline_text}\n"
            f"作业链接: {hw.detail_url}"
        )

        if fp in existing_items and not args.force:
            existing = existing_items[fp]
            old_event_id = existing.get("event_id")
            old_status = existing.get("status", "")
            old_title = existing.get("title", "")

            # 状态或标题有变化才更新
            if old_status != hw.status or old_title != hw.title:
                if old_event_id:
                    try:
                        update_event(token, calendar_id, old_event_id, {
                            "summary": summary,
                            "description": description,
                            "start_time": {
                                "timestamp": str(deadline_ts),
                                "timezone": "Asia/Shanghai",
                            },
                            "end_time": {
                                "timestamp": str(end_ts),
                                "timezone": "Asia/Shanghai",
                            },
                        })
                        updated_count += 1
                        existing_items[fp] = {
                            "event_id": old_event_id,
                            "title": hw.title,
                            "status": hw.status,
                            "synced_at": datetime.now().isoformat(),
                        }
                        print(f"[UPDATED] event_id={old_event_id} | {hw.title} | 状态: {old_status}→{hw.status}")
                    except Exception as exc:
                        print(f"[ERROR] 更新事件失败: {hw.title} - {exc}")
                else:
                    skipped_count += 1
                    print(f"[SKIP] {hw.title} (无 event_id，跳过)")
            else:
                skipped_count += 1
                print(f"[SKIP] {hw.title} (无变化)")
        else:
            # 新条目 — 创建事件
            try:
                data = create_event(
                    token, calendar_id,
                    summary=summary,
                    description=description,
                    start_ts=deadline_ts,
                    end_ts=end_ts,
                )
                event_id = data.get("data", {}).get("event", {}).get("event_id")
                created_count += 1
                existing_items[fp] = {
                    "event_id": event_id,
                    "title": hw.title,
                    "status": hw.status,
                    "synced_at": datetime.now().isoformat(),
                }
                print(f"[CREATED] event_id={event_id} | {hw.title} | {hw.deadline_date.strftime('%Y-%m-%d')}")
                time.sleep(0.2)
            except Exception as exc:
                print(f"[ERROR] 创建事件失败: {hw.title} - {exc}")

    # ── 保存状态 ──
    state["items"] = existing_items
    save_state(state)

    print(f"\n[DONE] 创建 {created_count} 条, 更新 {updated_count} 条, 跳过 {skipped_count} 条")


def main() -> None:
    parser = argparse.ArgumentParser(description="学者网作业 → 飞书日历")
    parser.add_argument("--url", default=HOMEWORK_URL, help="作业列表页 URL")
    parser.add_argument("--limit", type=int, default=5, help="最多同步多少条作业")
    parser.add_argument("--calendar-id", default="", help="目标飞书日历 ID")
    parser.add_argument("--dry-run", action="store_true", help="只抓取打印，不写飞书")
    parser.add_argument("--force", action="store_true", help="忽略去重，强制重新创建事件")
    args = parser.parse_args()

    try:
        sync(args)
    except RuntimeError as exc:
        print(f"[FATAL] {exc}")
        exit(1)


if __name__ == "__main__":
    main()
