"""学者网作业抓取接口（纯数据流出，可导入复用）。

提供可导入的 fetch_homework() 函数，返回作业列表 dict，
可自行处理数据（输出 JSON、接入飞书等）。

CLI 用法：
    python fetch_homework.py                              # 抓取默认作业页全部作业
    python fetch_homework.py --url <作业页URL>             # 抓取指定作业页
    python fetch_homework.py --limit 10                   # 最多输出 10 条
    python fetch_homework.py --all                        # 不过滤无截止时间的作业
    python fetch_homework.py --output homework.json       # 输出到文件


依赖：pip install requests beautifulsoup4 python-dotenv（另需系统安装 Node.js）
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from typing import Optional

import requests
from requests.exceptions import ProxyError, RequestException

from scholat_sync.auth import login_scholat
from scholat_sync.config import HOMEWORK_URL
from scholat_sync.homework import parse_homework_page, sort_by_deadline


def fetch_homework(
    session: requests.Session,
    url: Optional[str] = None,
    limit: int = 0,
    include_no_deadline: bool = False,
) -> dict:
    """抓取学者网课程作业列表。

    参数：
    - session: 已登录的 requests.Session
    - url: 作业列表页 URL，默认使用 .env 配置的 HOMEWORK_URL
    - limit: 最多返回条数，0=全部
    - include_no_deadline: 是否包含无截止时间的作业

    返回：
    {
        "url": str,
        "total": int,
        "count": int,
        "homeworks": [HomeworkItem, ...]
    }
    """
    if url is None:
        url = HOMEWORK_URL

    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    homeworks = parse_homework_page(resp.text, url)
    if not homeworks:
        return {"url": url, "total": 0, "count": 0, "homeworks": []}

    homeworks = sort_by_deadline(homeworks)

    if not include_no_deadline:
        homeworks = [hw for hw in homeworks if hw.deadline_date is not None]

    total = len(homeworks)
    if limit > 0:
        homeworks = homeworks[:limit]

    # 将 HomeworkItem 转为可序列化的 dict
    def _serialize(hw):
        d = asdict(hw)
        if d["deadline_date"]:
            d["deadline_date"] = d["deadline_date"].strftime("%Y-%m-%d %H:%M")
        return d

    return {
        "url": url,
        "total": total,
        "count": len(homeworks),
        "homeworks": [_serialize(hw) for hw in homeworks],
    }


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取学者网课程作业")
    parser.add_argument("--url", default=HOMEWORK_URL, help="作业列表页 URL")
    parser.add_argument("--limit", type=int, default=0, help="最多输出条数（0=全部）")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="include_no_deadline",
        help="包含无截止时间的作业（默认跳过）",
    )
    parser.add_argument(
        "--output", "-o", type=str, help="输出 JSON 文件路径，默认 stdout"
    )
    parser.add_argument("--compact", action="store_true", help="紧凑 JSON 输出")
    args = parser.parse_args()

    session = _create_session()

    print("[INFO] 登录学者网...", file=sys.stderr)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            login_scholat(session)
            break
        except ProxyError:
            if attempt < max_retries - 1:
                print("[WARN] 代理连接异常，重试中...", file=sys.stderr)
            else:
                print("[FATAL] 登录失败：多次代理连接异常", file=sys.stderr)
                sys.exit(1)
        except RequestException as exc:
            print(f"[FATAL] 登录请求失败: {exc}", file=sys.stderr)
            sys.exit(1)
    print("[INFO] 登录成功", file=sys.stderr)

    try:
        result = fetch_homework(
            session,
            url=args.url,
            limit=args.limit,
            include_no_deadline=args.include_no_deadline,
        )
        print(
            f"[INFO] 识别到作业 {result['total']} 条，输出 {result['count']} 条",
            file=sys.stderr,
        )
    except RequestException as exc:
        print(f"[FATAL] 获取作业页失败: {exc}", file=sys.stderr)
        sys.exit(1)

    indent = None if args.compact else 2
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[INFO] 已写入 {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
