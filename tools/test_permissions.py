#!/usr/bin/env python3
"""飞书日历权限测试工具。

验证飞书 API 的核心权限是否正常：日历 CRUD、事件 CRUD、ACL 增删。

用法：
    python tools/test_permissions.py
"""

import time

from scholat_sync.config import APP_ID, APP_SECRET, EMAIL, PHONE, TIMEZONE
from scholat_sync.feishu import (
    add_calendar_subscriber,
    create_calendar,
    delete_calendar,
    delete_event,
    feishu_request,
    get_calendar,
    get_event,
    get_tenant_access_token,
    get_user_open_id,
    remove_calendar_subscriber,
    update_calendar,
    update_event,
)


class TestRunner:
    """测试结果记录器。"""

    def __init__(self) -> None:
        self.results = []

    def record(self, name: str, passed: bool, detail: str) -> None:
        self.results.append({"name": name, "passed": passed, "detail": detail})
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name} - {detail}")

    def summary(self) -> None:
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        print("\n========== 权限测试汇总 ==========")
        print(f"通过: {passed}/{total}")
        for r in self.results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"- [{status}] {r['name']}: {r['detail']}")


def run() -> None:
    runner = TestRunner()
    token = get_tenant_access_token()
    runner.record("auth.get_token", True, "获取 tenant_access_token 成功")

    created_calendar_id = None
    created_event_id = None
    created_acl_id = None

    try:
        # 创建日历
        created_calendar_id = create_calendar(
            token, f"权限测试日历-{int(time.time())}", "自动化权限测试专用日历"
        )
        runner.record("calendar.create", True, f"calendar_id={created_calendar_id}")

        # 读取日历
        data = get_calendar(token, created_calendar_id)
        runner.record("calendar.read", data.get("code") == 0, data.get("msg", ""))

        # 更新日历
        data = update_calendar(token, created_calendar_id, {"description": "自动化权限测试-已更新"})
        runner.record("calendar.update", data.get("code") == 0, data.get("msg", ""))

        # 创建事件
        start_ts = int(time.time()) + 300
        end_ts = start_ts + 1800
        data = feishu_request(
            "POST",
            f"https://open.feishu.cn/open-apis/calendar/v4/calendars/{created_calendar_id}/events",
            token,
            payload={
                "summary": "权限测试事件",
                "description": "自动化创建",
                "start_time": {"timestamp": str(start_ts), "timezone": TIMEZONE},
                "end_time": {"timestamp": str(end_ts), "timezone": TIMEZONE},
            },
        )
        if data.get("code") == 0:
            created_event_id = data["data"]["event"]["event_id"]
            runner.record("event.create", True, f"event_id={created_event_id}")
        else:
            runner.record("event.create", False, str(data))

        # 读取事件
        if created_event_id:
            data = get_event(token, created_calendar_id, created_event_id)
            runner.record("event.read", data.get("code") == 0, data.get("msg", ""))

            data = update_event(
                token, created_calendar_id, created_event_id,
                {"summary": "权限测试事件-已更新"},
            )
            runner.record("event.update", data.get("code") == 0, data.get("msg", ""))

        # ACL 测试
        open_id = get_user_open_id(token, EMAIL, PHONE)
        if open_id:
            data = add_calendar_subscriber(token, created_calendar_id, open_id, role="reader")
            if data.get("code") == 0:
                acl_data = data.get("data", {})
                created_acl_id = (
                    acl_data.get("acl_id")
                    or acl_data.get("acl", {}).get("acl_id")
                    or acl_data.get("id")
                )
                if created_acl_id:
                    runner.record("acl.add_subscriber", True, f"acl_id={created_acl_id}")
                else:
                    runner.record("acl.add_subscriber", False, f"添加成功但未返回 acl_id: {data}")
            else:
                runner.record("acl.add_subscriber", False, str(data))

            if created_acl_id:
                data = remove_calendar_subscriber(token, created_calendar_id, created_acl_id)
                runner.record("acl.remove_subscriber", data.get("code") == 0, data.get("msg", ""))
        else:
            runner.record("acl.add_subscriber", False, "未能通过 EMAIL/PHONE 获取 open_id")

    except Exception as exc:
        runner.record("unexpected_error", False, str(exc))

    finally:
        # 清理
        if created_event_id and created_calendar_id:
            try:
                data = delete_event(token, created_calendar_id, created_event_id)
                runner.record("event.delete", data.get("code") == 0, data.get("msg", ""))
            except Exception as exc:
                runner.record("event.delete", False, str(exc))

        if created_calendar_id:
            try:
                data = delete_calendar(token, created_calendar_id)
                runner.record("calendar.delete", data.get("code") == 0, data.get("msg", ""))
            except Exception as exc:
                runner.record("calendar.delete", False, str(exc))

        runner.summary()


if __name__ == "__main__":
    run()
