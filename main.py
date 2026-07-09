# main.py
import time
import datetime 
from appium import webdriver
from appium.options.android import UiAutomator2Options
import config
from utils import (
    click_element,
    click_button_in_punch_card,
    check_and_start_appium,
    ensure_adb_connected,
    logger,
    check_time_tip_presence,
    write_punch_state,
    read_punch_state,
    should_skip_today,
    save_screenshot
)

def _build_options(skip_install=False):
    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.automation_name = 'UiAutomator2'
    options.device_name = 'Android'
    options.no_reset = True
    options.app_package = config.APP_PACKAGE
    options.app_activity = config.APP_ACTIVITY
    if skip_install:
        options.skip_server_installation = True
        options.skip_device_initialization = True
    return options

def init_driver():
    try:
        return webdriver.Remote(config.APPIUM_SERVER_URL, options=_build_options())
    except Exception as e:
        if 'INSTALL_FAILED_USER_RESTRICTED' in str(e):
            logger.warning("⚠️ APK 安装被拒绝 (USB安装权限已关闭)，跳过安装步骤后重试...")
            return webdriver.Remote(config.APPIUM_SERVER_URL, options=_build_options(skip_install=True))
        raise

def run_task():                                 
    current_hour = datetime.datetime.now().hour
    logger.info(f"⌚️ 当前小时数: {current_hour}点")

    # ==========================================
    # -1. 检查是否应该跳过今天的打卡
    # ==========================================
    if should_skip_today():
        logger.info("🚫 根据配置，今日跳过打卡，任务提前结束。")
        return

    # 如果是晚上，先判断早上是否需要打卡
    if current_hour >= 14:
        need_evening = read_punch_state()
        if not need_evening:
            logger.info("⛔ 早上未检测到打卡 Tip，晚上无需打卡，任务提前结束。")
            return

    # ==========================================
    # 0. 环境自检
    # ==========================================
    
    # 1. 先检查 ADB 设备 (使用 config.TIMEOUT 作为循环等待时间)
    if not ensure_adb_connected(timeout=config.TIMEOUT):
        return # 找不到设备，直接退出

    # 2. 再检查 Appium 服务
    if not check_and_start_appium(port=4723):
        return # 服务起不来，直接退出

    driver = None
    try:
        logger.info("🚀 自动化任务启动...")
        driver = init_driver()
        
        # ==========================================
        # 1. 公共步骤：进入假勤
        # ==========================================
        # 1.1 点击工作台
        if not click_element(driver, config.SELECTORS['tab_workplace'], "工作台Tab", config.TIMEOUT):
            return

        # 1.2 点击假勤
        if not click_element(driver, config.SELECTORS['icon_attendance'], "假勤应用", config.TIMEOUT):
            return

        # ==========================================
        # 2. 分支逻辑：根据时间决定是上班还是下班
        # ==========================================
        # 设定分界线：14点 (下午2点)
        if current_hour < 14:
            # ☀️ 上午模式：执行上班打卡 (找按钮点点点)
            logger.info("☀️ 检测为【上班模式】，准备寻找打卡按钮...")
            
            target_prefix = config.ATTENDANCE_CONFIG['time_tip_prefix']
            target_btn = config.ATTENDANCE_CONFIG['button_text']

            need_evening = check_time_tip_presence(driver, target_prefix, config.TIMEOUT)
            write_punch_state(need_evening)

            if need_evening:
                if click_button_in_punch_card(driver, target_prefix, target_btn, config.TIMEOUT):
                    logger.info("🎉 上班打卡动作完成！等待确认...")
                    time.sleep(5)
                else:
                    logger.info("⚠️ 未找到上班打卡按钮 (可能已打卡或不在时间内)。")
            else:
                logger.info("⛔ 未检测到打卡 Tip，晚上将跳过打卡。")

        else:
            # 🌙 下午/晚上模式：执行下班逻辑 (发呆10秒)
            logger.info("🌙 检测为【下班模式】，仅需保持页面开启...")
            
            logger.info("⏳ 正在停留等待 10 秒...")
            time.sleep(10)
            logger.info("✅ 下班流程执行完毕。")

    except Exception as e:
        logger.error(f"💥 发生全局异常: {e}")
        if driver:
            save_screenshot(driver, "global_exception")
    finally:
        # ==========================================
        # 3. 最终步骤：关闭应用 (terminate_app)
        # ==========================================
        if driver:
            try:
                logger.info("🔚 正在关闭应用...")
                driver.terminate_app(config.APP_PACKAGE)
                driver.quit()
            except Exception:
                pass
            logger.info("🏁 驱动已关闭，任务结束。")

if __name__ == '__main__':
    run_task()