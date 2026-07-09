# config.py

# App 基础信息
APP_PACKAGE = 'com.ss.android.lark'
APP_ACTIVITY = 'com.ss.android.lark.main.app.MainActivity'
# Appium Server 地址
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'
TIMEOUT = 20  # 默认超时时间(秒)

# 状态文件路径 (单条记录，覆盖写入，防止文件变大)
STATE_FILE_PATH = '/Users/wangwl.net/tyc/lark_auto/punch_state.json'

# 跳过打卡文件路径 (文件中每行为 YYYY-MM-DD 格式的日期)
SKIP_DATES_FILE = '/Users/wangwl.net/Library/Mobile Documents/iCloud~md~obsidian/Documents/iphone-obsidian-vault/clock-in-skip.md'

# 失败截图保存目录
SCREENSHOT_DIR = '/Users/wangwl.net/tyc/lark_auto/screenshots/'


# 元素定位配置
SELECTORS = {
    # 底部导航栏 - 工作台label
    'tab_workplace': '//android.widget.TextView[@text="工作台"]',

    # 工作台 - 假勤图标label
    'icon_attendance': '//android.widget.TextView[@text="假勤"]',
}


# 业务变量 
ATTENDANCE_CONFIG = {
    # 匹配 Tip 的前缀，"应上班 09:" 
    'time_tip_prefix': '应上班 09:',
    
    # 按钮上的具体文字，"上班打卡"
    'button_text': '上班打卡'
}






