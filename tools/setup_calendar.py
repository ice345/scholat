"""飞书日历初始化工具：创建日历 + 添加订阅者。

首次使用飞书同步前，需要先创建日历并把你自己添加为订阅者。
此工具一次性完成这两步。

用法：
    python tools/setup_calendar.py
"""

from scholat_sync.config import APP_ID, APP_SECRET, EMAIL, PHONE
from scholat_sync.feishu import (
    add_calendar_subscriber,
    create_calendar,
    get_tenant_access_token,
    get_user_open_id,
)

CALENDAR_NAME = "学者网同步日历"
CALENDAR_DESC = "自动同步学者网的个人课程和组织动态"


def main() -> None:
    token = get_tenant_access_token()
    print(f"[INFO] 获取 Token 成功")

    calendar_id = create_calendar(token, CALENDAR_NAME, CALENDAR_DESC)
    print(f"[INFO] 日历创建成功: {calendar_id}")
    print(f"请将此 ID 填入 .env 的 CALENDAR_ID")

    if EMAIL or PHONE:
        open_id = get_user_open_id(token, EMAIL, PHONE)
        if open_id:
            add_calendar_subscriber(token, calendar_id, open_id, role="writer")
            print(f"[INFO] 已添加订阅者（可编辑）：open_id={open_id}")
        else:
            print("[WARN] 无法获取用户 open_id，请检查 EMAIL/PHONE 配置和应用权限")
    else:
        print("[WARN] 未配置 EMAIL/PHONE，跳过订阅者添加")


if __name__ == "__main__":
    main()
