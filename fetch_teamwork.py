"""学者网团队协作平台帖子抓取接口（纯数据流出，可导入复用）。

提供可导入的 fetch_teamwork() 函数，返回团队帖子列表 dict，
可自行处理数据（输出 JSON、接入飞书等）。

预置团队：
  计算机团委       id=671,  nav=3
  计算机学生会     id=1253, nav=3
  计算机党建中心   id=2086, nav=4
  2022级          id=1473, nav=4
  2023级          id=1136, nav=3
  2024级          id=2157, nav=4
  研究生           id=1259, nav=3

CLI 用法：
    python fetch_teamwork.py                          # 抓取全部预置团队
    python fetch_teamwork.py --team 团委              # 抓取指定团队（模糊匹配名称）
    python fetch_teamwork.py --id 671 --nav 3         # 抓取指定 ID 的团队
    python fetch_teamwork.py --max-pages 2            # 每个团队最多抓取 2 页
    python fetch_teamwork.py --detail                 # 同时抓取每个帖子的详情
    python fetch_teamwork.py --output posts.json      # 输出到文件


依赖：pip install requests beautifulsoup4 python-dotenv（另需系统安装 Node.js）
"""

import argparse
import json
import sys
from dataclasses import asdict
from typing import Optional

import requests

from scholat_sync.auth import login_scholat
from scholat_sync.teamwork import fetch_post_detail, fetch_teamwork_posts

# 预置团队配置
PRESET_TEAMS: dict[str, dict] = {
    "计算机团委": {"id": 671, "nav": 3},
    "计算机学生会": {"id": 1253, "nav": 3},
    "计算机党建中心": {"id": 2086, "nav": 4},
    "2022级": {"id": 1473, "nav": 4},
    "2023级": {"id": 1136, "nav": 3},
    "2024级": {"id": 2157, "nav": 4},
    "研究生": {"id": 1259, "nav": 3},
}


def find_team(name: str) -> Optional[dict]:
    """模糊匹配团队名称。"""
    name_lower = name.strip().lower()
    for team_name, config in PRESET_TEAMS.items():
        if name_lower in team_name.lower():
            return {"name": team_name, **config}
    return None


def fetch_teamwork(
    session: requests.Session,
    teams: list[tuple[str, dict]],
    max_pages: Optional[int] = None,
    with_detail: bool = False,
) -> dict:
    """抓取团队协作平台帖子。

    参数：
    - session: 已登录的 requests.Session
    - teams: 要抓取的团队列表，格式 [(team_name, {"id": int, "nav": int}), ...]
    - max_pages: 每个团队最大抓取页数，None=全部
    - with_detail: 是否同时抓取帖子详情

    返回：
    {
        "teams": [
            {
                "name": str,
                "id": int,
                "nav": int,
                "post_count": int,
                "posts": [
                    {  # TeamworkPost + 可选 detail 字段
                        "index": int,
                        "title": str,
                        "detail_url": str,
                        "visibility": str,
                        "publisher": str,
                        "publish_time": str,
                        "view_count": int,
                        "source_team": str,
                        "source_url": str,
                        "detail": {...},  # 仅 with_detail=True 时存在
                    }
                ]
            }
        ]
    }
    """
    result_teams: list[dict] = []

    for team_name, config in teams:
        team_id = config["id"]
        nav = config["nav"]

        posts = fetch_teamwork_posts(
            session,
            team_id=team_id,
            nav=nav,
            max_pages=max_pages,
        )

        team_data: dict = {
            "name": team_name,
            "id": team_id,
            "nav": nav,
            "post_count": len(posts),
            "posts": [],
        }

        for post in posts:
            post_dict = asdict(post)

            if with_detail and post.detail_url:
                try:
                    detail = fetch_post_detail(session, post.detail_url)
                    post_dict["detail"] = detail
                except Exception:
                    pass

            team_data["posts"].append(post_dict)

        result_teams.append(team_data)

    return {"teams": result_teams}


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取学者网团队协作平台帖子")
    parser.add_argument("--team", type=str, help="团队名称（模糊匹配）")
    parser.add_argument("--id", type=int, help="团队 ID")
    parser.add_argument("--nav", type=int, default=3, help="导航标签，默认 3")
    parser.add_argument(
        "--max-pages", type=int, default=None, help="每个团队最大抓取页数"
    )
    parser.add_argument("--detail", action="store_true", help="同时抓取帖子详情")
    parser.add_argument(
        "--output", "-o", type=str, help="输出 JSON 文件路径，默认 stdout"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="格式化 JSON 输出（默认开启）",
    )
    parser.add_argument("--compact", action="store_true", help="紧凑 JSON 输出")
    args = parser.parse_args()

    # 确定要抓取的团队列表
    teams_to_fetch: list[tuple[str, dict]] = []

    if args.id:
        teams_to_fetch.append((f"团队{args.id}", {"id": args.id, "nav": args.nav}))
    elif args.team:
        matched = find_team(args.team)
        if not matched:
            print(f"[ERROR] 未匹配到团队: {args.team}", file=sys.stderr)
            print(f"预置团队: {', '.join(PRESET_TEAMS.keys())}", file=sys.stderr)
            sys.exit(1)
        name = matched.pop("name")
        teams_to_fetch.append((name, matched))
    else:
        for name, config in PRESET_TEAMS.items():
            teams_to_fetch.append((name, config.copy()))

    session = _create_session()

    print("[INFO] 登录学者网...", file=sys.stderr)
    login_scholat(session)
    print("[INFO] 登录成功", file=sys.stderr)

    for team_name, _ in teams_to_fetch:
        print(f"[INFO] 抓取: {team_name}", file=sys.stderr)

    result = fetch_teamwork(
        session,
        teams=teams_to_fetch,
        max_pages=args.max_pages,
        with_detail=args.detail,
    )

    for t in result["teams"]:
        print(f"[INFO] {t['name']}: 抓取到 {t['post_count']} 条帖子", file=sys.stderr)

    indent = 2 if args.pretty and not args.compact else None
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[INFO] 已写入 {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == "__main__":
    main()
