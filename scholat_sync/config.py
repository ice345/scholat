"""集中配置管理，全部从 .env 加载。"""

import os

from dotenv import load_dotenv

load_dotenv()

# 飞书凭证
APP_ID = os.environ["APP_ID"]
APP_SECRET = os.environ["APP_SECRET"]
FEISHU_CALENDAR_ID = os.getenv("CALENDAR_ID", "").strip()

# 学者网账号
SCHOLAT_USERNAME = os.getenv("SCHOLAT_USERNAME", "").strip()
SCHOLAT_PASSWORD = os.getenv("SCHOLAT_PASSWORD", "").strip()
SCHOLAT_LOGIN_URL = os.getenv("SCHOLAT_LOGIN_URL", "https://www.scholat.com/login.html")
SCHOLAT_HOME_URL = os.getenv("SCHOLAT_HOME_URL", "https://www.scholat.com/Phomepage.html")

# 飞书日历参数
SYNC_CALENDAR_NAME = os.getenv("SYNC_CALENDAR_NAME", "学者网自动同步")
SYNC_CALENDAR_DESC = os.getenv("SYNC_CALENDAR_DESC", "自动同步学者网组织与课程动态")

# 通用同步参数
STATE_FILE = os.getenv("SYNC_STATE_FILE", ".scholat_sync_state.json")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")
SECTION_KEYWORDS = ["我的动态", "我的课程"]

# 作业同步参数
HOMEWORK_URL = os.getenv(
    "SCHOLAT_HOMEWORK_TEST_URL",
    "https://www.scholat.com/course/S_homeworkList.html?courseId=100",
)
HOMEWORK_CALENDAR_ID = os.getenv("HOMEWORK_TEST_CALENDAR_ID", "").strip()
HOMEWORK_CALENDAR_NAME = os.getenv("HOMEWORK_TEST_CALENDAR_NAME", "学者网作业测试")
HOMEWORK_STATE_FILE = os.getenv("HOMEWORK_STATE_FILE", ".scholat_homework_sync_state.json")

# 用户信息（飞书订阅者查询用）
EMAIL = os.getenv("EMAIL", "").strip()
PHONE = os.getenv("PHONE", "").strip()
