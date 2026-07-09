# utils.py
import re
import socket
import subprocess
import logging
import time
import json
import datetime
import os
import config
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy

# 配置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def save_screenshot(driver, desc):
    """
    在失败现场截图并保存到 SCREENSHOT_DIR，文件名含时间戳和描述。
    截图失败不抛异常，不影响主流程。
    """
    try:
        os.makedirs(config.SCREENSHOT_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        safe_desc = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', desc)[:60]
        filepath = os.path.join(config.SCREENSHOT_DIR, f"{timestamp}_{safe_desc}.png")
        driver.save_screenshot(filepath)
        logger.info(f"📸 截图已保存: {filepath}")
    except Exception as e:
        logger.warning(f"⚠️ 截图失败 (不影响主流程): {e}")

def get_by_type(locator_value):
    if "id/" in locator_value or ":id" in locator_value:
        return AppiumBy.ID
    return AppiumBy.XPATH

def wait_for_stable_element(driver, locator_value, desc, timeout=10):
    """
    核心工具函数：获取一个【稳定】的元素。
    """
    check_interval = 2  # 你设置的考验期
    
    by_type = get_by_type(locator_value)
    end_time = time.time() + timeout
    
    logger.info(f"🛡️ [Stability Check] 开始监测元素稳定性: {desc}")

    # 1. 第一阶段：先确保元素出现在 DOM 里
    try:
        current_element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by_type, locator_value))
        )
    except TimeoutException:
        logger.error(f"❌ [Timeout] 元素在 {timeout}s 内根本未出现: {desc}")
        save_screenshot(driver, f"timeout_{desc}")
        return None

    # 2. 第二阶段：稳定性循环检测
    while time.time() < end_time:
        try:
            time.sleep(check_interval)
            current_element.is_enabled() 
            logger.info(f"✅ [Stable] 元素已稳定 (持续 {check_interval}s 有效): {desc}")
            return current_element

        except StaleElementReferenceException:
            logger.warning(f"🌊 [Reflow] 页面发生刷新，元素引用已失效，重新定位: {desc}...")
            try:
                current_element = driver.find_element(by_type, locator_value)
            except Exception:
                pass

    logger.error(f"🚫 [Unstable] 元素在 {timeout}s 内始终未能稳定: {desc}")
    save_screenshot(driver, f"unstable_{desc}")
    return None

def click_element(driver, locator_value, desc="未知元素", timeout=15):
    """业务函数：点击"""
    element = wait_for_stable_element(driver, locator_value, desc, timeout=timeout)
    
    if element:
        try:
            element.click()
            logger.info(f"🖱️ 点击执行完毕: {desc}")
            return True
        except Exception as e:
            logger.error(f"💥 点击动作失败: {e}")
            save_screenshot(driver, f"click_failed_{desc}")
            return False
    else:
        return False

# =======================================================
# 👇 新增：专门处理复杂的“卡片关联点击”逻辑
# =======================================================
def click_button_in_punch_card(driver, time_prefix, button_text, timeout=15):
    """
    根据文案找到对应的卡片，然后点击里面的按钮。
    逻辑：
    1. 找 text 以 time_prefix 开头的 Tip
    2. 找 Tip 的父级的兄弟节点 (punchArea)
    3. 找里面的 button_text
    """
    logger.info(f"🧩 启动组合定位逻辑: 寻找[{time_prefix}]旁边的[{button_text}]按钮...")

    # 构造组合 XPath (这是最稳健的方式，比分步查找更不易报错)
    # 解释：
    # 1. //android.widget.TextView[starts-with(@text, "...")]  --> 找到Tip
    # 2. /..                                                   --> 找到Tip的爸爸
    # 3. /following-sibling::android.view.View[contains(@resource-id, "punchArea")] --> 找爸爸的弟弟(Card)
    # 4. //android.widget.TextView[@text="..."]                --> 找Card里面的按钮
    
    combined_xpath = (
        f'//android.widget.TextView[starts-with(@text, "{time_prefix}")]'
        f'/../following-sibling::android.view.View[contains(@resource-id, "punchArea")]'
        f'//android.widget.TextView[@text="{button_text}"]'
    )

    return click_element(driver, combined_xpath, desc=f"组合定位按钮({button_text})", timeout=timeout)

def check_time_tip_presence(driver, time_prefix, timeout=10):
    """
    判断是否存在打卡 Tip 文案，用于决定晚上是否需要打卡。
    """
    tip_xpath = f'//android.widget.TextView[starts-with(@text, "{time_prefix}")]'
    element = wait_for_stable_element(driver, tip_xpath, desc=f"打卡Tip({time_prefix})", timeout=timeout)
    if element:
        logger.info(f"✅ 找到打卡 Tip: {time_prefix}")
        return True
    logger.info(f"⚠️ 未找到打卡 Tip: {time_prefix}")
    return False

def write_punch_state(need_evening):
    """
    覆盖写入当天的打卡状态。
    失败不会抛异常，避免影响后续写入。
    """
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    payload = {
        "date": date_str,
        "need_evening": bool(need_evening)
    }
    try:
        with open(config.STATE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        logger.info(f"📝 状态已写入: {payload}")
    except Exception as e:
        logger.error(f"💥 写入状态文件失败: {e}")

def read_punch_state():
    """
    读取当天的打卡状态。
    读取失败或解析失败时默认返回 True (晚上需要打卡)。
    """
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    try:
        with open(config.STATE_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data.get("date") != date_str:
            logger.warning(f"⚠️ 状态日期不匹配，默认需要打卡。当前: {date_str}, 文件: {data.get('date')}")
            return True

        return bool(data.get("need_evening", True))
    except Exception as e:
        logger.error(f"💥 读取状态文件失败，默认需要打卡: {e}")
        return True

# 查看Appium后台进程：lsof -i :4723 或者 ps ，找到对应的pid，然后 kill -9 <PID>
def check_and_start_appium(port=4723):
    """
    检查 Appium 是否启动，如果没有启动则自动启动。
    """
    logger.info(f"🕵️ [System Check] 正在检查 Appium 服务 (Port {port})...")
    
    # 1. 定义检测端口的内部函数
    def is_port_open(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1) # 设置超时时间，避免卡住
            return s.connect_ex((host, port)) == 0

    # 2. 如果端口已开，直接返回
    if is_port_open('127.0.0.1', port):
        logger.info("✅ Appium 服务已在运行。")
        return True

    # 3. 如果端口未开，尝试启动
    logger.warning("⚠️ Appium 服务未运行，正在尝试后台启动...")
    try:
        # 使用 subprocess 在后台启动 appium
        # stdout=subprocess.DEVNULL 表示把 Appium 的那一大堆日志丢掉，保持终端清爽
        # 如果你想看 Appium 日志，可以去掉 stdout/stderr 参数
        subprocess.Popen(['appium'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 4. 循环等待服务启动完成 (最多等 20秒)
        for i in range(20):
            time.sleep(1)
            if is_port_open('127.0.0.1', port):
                logger.info("🚀 Appium 服务启动成功！")
                return True
            logger.info(f"   ⏳ 等待 Appium 启动 ({i+1}/20s)...")
            
        logger.error("❌ Appium 启动超时，请检查是否安装了 appium 或手动启动。")
        return False

    except FileNotFoundError:
        logger.error("❌ 找不到 'appium' 命令。请确保配置了环境变量。")
        return False
    except Exception as e:
        logger.error(f"💥 启动 Appium 时发生未知错误: {e}")
        return False

# =======================================================
# ADB 设备检查与重连逻辑
# =======================================================
def ensure_adb_connected(timeout=20):
    """
    确保 ADB 能找到设备。如果找不到，尝试重启 ADB Server 并循环检查。
    :param timeout: 循环检查的最大时长(秒)
    """
    logger.info("🔌 [ADB Check] 正在检查设备连接状态...")
    
    def get_device_count():
        try:
            # 运行 adb devices 获取列表
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            output = result.stdout.strip()
            # 过滤空行，第一行通常是 List of devices attached
            lines = [line for line in output.split('\n') if line.strip()]
            # 如果大于1行，说明有设备列表
            return len(lines) > 1
        except Exception:
            return False

    # 1. 第一次快速检查
    if get_device_count():
        logger.info("✅ ADB 已检测到设备。")
        return True

    # 2. 如果没找到，尝试重启 ADB
    logger.warning("⚠️ ADB 未找到设备，尝试重启 ADB Server...")
    try:
        subprocess.run(['adb', 'kill-server'])
        time.sleep(1)
        subprocess.run(['adb', 'start-server'])
        # 注意：start-server 后不要立刻放弃，需要进入循环等待 USB 握手
    except Exception as e:
        logger.error(f"💥 重启 ADB 失败: {e}")
        return False

    # 3. 循环检查 (直到超时)
    logger.info(f"⏳ 正在循环等待设备上线 (超时: {timeout}s)...")
    end_time = time.time() + timeout
    
    time.sleep(2)
    while time.time() < end_time:
        if get_device_count():
            logger.info("✅ 重启 ADB 后成功检测到设备！")
            return True
        # 还没找到，稍微等一下继续找
        time.sleep(2)
        
    logger.error(f"❌ 致命错误：在 {timeout}s 内未能找到连接的 Android 设备。")
    logger.error("   请检查：1.手机是否连接 2.是否开启了USB调试 3.USB配置是否为文件传输")
    return False

def ensure_icloud_file_synced(file_path, timeout=60):
    """
    确保 iCloud 文件已同步到本地最新版本。
    先执行 brctl download 触发下载，然后轮询检查文件大小直到稳定。
    
    :param file_path: iCloud 文件绝对路径
    :param timeout: 最大等待时间(秒)
    :return: True 表示文件已同步，False 表示同步失败
    """
    logger.info(f"📥 [iCloud Sync] 开始同步文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"❌ 文件不存在: {file_path}")
        return False
    
    # 1. 执行 brctl download 触发下载
    try:
        logger.info("⬇️ 执行 brctl download 触发同步...")
        result = subprocess.run(
            ['brctl', 'download', file_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.warning(f"⚠️ brctl download 返回非零: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ brctl download 超时，继续检查文件...")
    except Exception as e:
        logger.warning(f"⚠️ brctl download 执行失败: {e}，继续检查文件...")
    
    # 2. 轮询检查文件大小直到稳定
    check_interval = 10  # 10秒间隔
    last_size = -1
    
    end_time = time.time() + timeout
    logger.info(f"⏳ 开始轮询检查文件大小 (间隔{check_interval}s, 超时{timeout}s)...")
    
    while time.time() < end_time:
        try:
            current_size = os.path.getsize(file_path)
            logger.info(f"📊 当前文件大小: {current_size} bytes")
            
            if last_size != -1 and current_size == last_size:
                logger.info("✅ 文件大小稳定，同步完成！")
                return True
            
            if current_size != last_size:
                logger.info("⟳ 文件大小变化，继续等待...")
            
            last_size = current_size
            time.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"❌ 检查文件大小时出错: {e}")
            return False
    
    logger.error(f"❌ 文件同步超时 ({timeout}s)")
    return False

def should_skip_today():
    """
    读取跳过日期文件，检查当前日期是否在跳过列表中。
    先确保 iCloud 文件已同步到最新，然后读取并检查日期。
    
    :return: True 表示应该跳过今天，False 表示不跳过
    """
    file_path = config.SKIP_DATES_FILE
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"📅 检查是否需要跳过今天的打卡 (今天: {today})")
    
    # 先确保 iCloud 文件同步到最新
    if not ensure_icloud_file_synced(file_path, timeout=60):
        logger.warning("⚠️ iCloud 文件同步失败，尝试读取现有文件")
    
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ 跳过日期文件不存在: {file_path}，继续执行打卡")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"📄 跳过日期文件内容:\n{content.strip()}")
            
            # 重新定位到文件开头进行匹配
            f.seek(0)
            for line in f:
                # 去除首尾空格
                date_str = line.strip()
                if date_str == today:
                    logger.info(f"🚫 匹配到跳过日期: {today}，今日将跳过打卡！")
                    return True
        
        logger.info(f"✓ 今日 ({today}) 不在跳过列表中，继续执行打卡")
        return False
        
    except Exception as e:
        logger.error(f"❌ 读取跳过日期文件时出错: {e}，继续执行打卡")
        return False