# 学者网 → 飞书日历 同步工具

自动登录[学者网](https://www.scholat.com)，抓取**课程作业**和**栏目动态**，写入飞书日历。

---

>[!Tip]
>因为我的学者网没有什么信息和动态,只有之前操作系统的作业这个信息.因此,我以他作为测试对象,如果你们的学者网有更多信息和动态,可以在 `sync_general.py` 里添加更多的解析规则,来适配你们的学者网.

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env（见下方说明）

# 3. 先干跑预览（不写飞书）
python sync_homework.py --dry-run --limit 5

# 4. 确认无误后正式同步
python sync_homework.py --limit 5
```

---

## 文件结构

```
scholat/
├── README.md                       # 本文件
├── requirements.txt                # Python 依赖
├── .env                            # 配置（账号、密钥、日历 ID）
├── .scholat_sync_state.json        # 去重状态（通用同步，自动生成）
├── .scholat_homework_sync_state.json  # 去重状态（作业同步，自动生成）
│
├── sync_homework.py                # [日常使用] 作业 → 飞书日历
├── sync_general.py                 # [按需使用] 通用栏目 → 飞书日历
│
├── scholat_sync/                   # 核心逻辑包
│   ├── __init__.py
│   ├── config.py                   # 配置加载（所有常量从 .env 读取）
│   ├── auth.py                     # 学者网登录（DES 加密 + 表单提交）
│   ├── feishu.py                   # 飞书 API 封装（token、日历、事件、ACL）
│   ├── models.py                   # 数据模型：ScheduleItem, HomeworkItem
│   ├── homework.py                 # 作业页解析 + 截止时间排序 + 去重
│   └── scraper.py                  # 通用栏目抓取 + 日期识别 + 去重
│
└── tools/
    ├── setup_calendar.py           # [一次性] 创建飞书日历 + 添加订阅者
    └── test_permissions.py         # [排障用] 飞书 API 权限全量测试
```

---

## .env 配置说明

```ini
# ---- 飞书应用凭证（必填） ----
APP_ID=cli_xxxxxxxxxxxxxx
APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxx

# ---- 飞书日历 ID（必填） ----
# 从 tools/setup_calendar.py 创建后获取
CALENDAR_ID=xxxxxxxxxx@group.calendar.feishu.cn

# ---- 学者网账号（必填） ----
SCHOLAT_USERNAME=your_email@example.com
SCHOLAT_PASSWORD=your_password

# ---- 飞书用户信息（订阅用） ----
EMAIL=your_email@example.com
PHONE=138xxxxxxxx

# ---- 可选参数 ----
TIMEZONE=Asia/Shanghai
SCHOLAT_HOMEWORK_TEST_URL=https://www.scholat.com/course/S_homeworkList.html?courseId=100
```

以下为我的一个配置:

```ini
APP_ID=
APP_SECRET=
CALENDAR_ID=
PHONE=
EMAIL=

SCHOLAT_USERNAME=
SCHOLAT_PASSWORD=
SCHOLAT_LOGIN_URL=
SCHOLAT_HOME_URL=
SYNC_CALENDAR_NAME=
SYNC_CALENDAR_DESC=
SYNC_STATE_FILE=
TIMEZONE=

SCHOLAT_HOMEWORK_TEST_URL=
HOMEWORK_TEST_CALENDAR_ID=
HOMEWORK_TEST_CALENDAR_NAME=学者网作业测试
```

---

## 使用场景

### 场景一：同步课程作业（日常最常用）

```bash
# 预览即将创建的事件
python sync_homework.py --dry-run --limit 5

# 正式同步（按截止时间排序，最早的先创建）
python sync_homework.py --limit 5

# 指定其他课程页面
python sync_homework.py --url "https://www.scholat.com/course/S_homeworkList.html?courseId=XXX" --limit 10

# 强制重新创建（忽略去重状态）
python sync_homework.py --force --limit 5
```

行为说明：
- 登录学者网 → 抓取作业列表 → 按截止时间升序排序
- 自动过滤无截止时间的作业（无法创建事件）
- 事件日期使用实际截止日期，时间设为当天 20:00，时长 1 小时
- 通过 SHA1 指纹去重，重复运行不会创建重复事件
- 已存在的作业如果状态/标题有变化，自动更新飞书事件
- 无截止时间的作业会被跳过

### 场景二：同步通用栏目动态

```bash
# 预览
python sync_general.py --dry-run --per-section-limit 10

# 正式同步
python sync_general.py --per-section-limit 10
```

行为说明：
- 登录学者网 → 扫描首页"我的动态""我的课程"栏目
- 从栏目页面中提取包含日期信息的条目
- 通过 SHA1 指纹去重（状态文件 `.scholat_sync_state.json`）
- 仅同步新增条目

### 场景三：首次初始化

```bash
# 创建飞书日历并将自己添加为订阅者
python tools/setup_calendar.py
# → 输出 calendar_id，将其填入 .env 的 CALENDAR_ID
```

### 场景四：排障 / 验证权限

```bash
# 全量测试飞书 API 权限（日历/事件/ACL 的 CRUD）
python tools/test_permissions.py
```

