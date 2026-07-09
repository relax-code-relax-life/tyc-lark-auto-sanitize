# Project: Lark Auto Attendance (Android/Appium)

## 1. Project Overview

This project is an automated script to perform "Clock In" and "Clock Out" actions on the Lark (Feishu) Android app using Appium and Python. It runs on a Mac Mini connected to a Xiaomi Android device. Morning runs decide whether an evening punch is required and persist that decision for later.

**Skip Date Feature**: The script supports skipping punch-ins on specific dates by reading a date list from an iCloud-synced file. Before each run, it checks if today's date is in the skip list and exits early if matched.

## 2. Tech Stack & Environment

- Language: Python 3.10+ (Miniconda environment: `lark_auto`)
- Framework: Appium (UiAutomator2 Driver), Selenium WebDriver
- Hardware: Mac Mini (Host), Xiaomi Phone (Target)
- Shell: Zsh (controlled via `run.sh` and `exec.sh`)

## 3. Project Structure & Responsibilities

- `exec.sh` (Execution Entry):
  - Performs the actual punch-in logic. Can be run standalone manually or called by `run.sh`.
  - Dual-output logging: Uses `exec > >(tee -a run.log) 2>&1` at the top, so all output (stdout + stderr) is simultaneously printed to the console and appended to `run.log`, regardless of how the script is invoked.
  - Loads environment: `source ~/.zshrc` + `export PATH`.
  - Changes to the project directory.
  - Invokes `main.py`.

- `main.py` (Controller):
  - Entry point of the automation.
  - Skip Date Check: Before execution, calls `should_skip_today()` to check if today is in the skip list. If matched, exits immediately.
  - Time-based Logic:
    - Morning (< 14:00): Navigates to "Attendance" -> Finds specific card via text matching -> Clicks "Clock In".
    - Morning (< 14:00): Checks the time-tip presence, writes the result to state, and only clicks when the tip exists.
    - Evening (>= 14:00): Reads state; if no morning tip was found, skips the run early; otherwise navigates to "Attendance" -> Waits 10s (Keep Alive) -> Exits.
  - Performs environment self-checks (`ensure_adb_connected`, `check_and_start_appium`) before execution.
  - On global exception, calls `save_screenshot(driver, "global_exception")` to capture failure state.
  - `_build_options(skip_install=False)`: Builds `UiAutomator2Options`. When `skip_install=True`, adds `skip_server_installation` and `skip_device_initialization` to bypass Appium helper APK installation.
  - `init_driver()`: Resilient driver init with fallback — first attempts normal initialization; if `INSTALL_FAILED_USER_RESTRICTED` is raised (Xiaomi USB install permission disabled), retries with `skip_install=True`; any other error is re-raised.

- `utils.py` (Core Logic / Toolbelt):
  - `save_screenshot`: Saves a timestamped PNG to `SCREENSHOT_DIR` on failure. Called automatically by `wait_for_stable_element` (timeout/unstable), `click_element` (click failed), and `main.py` (global exception). Never raises — failure is swallowed to avoid disrupting the main flow.
  - `ensure_adb_connected`: Checks for ADB devices. If missing, attempts to restart ADB server or connect via Wireless ADB (TCP/IP). Handles "Device Offline" or "Unauthorized" loops.
  - `check_and_start_appium`: Checks port 4723. If occupied, reuses it; if free, launches Appium in a subprocess.
  - `wait_for_stable_element`: CRITICAL. Implements a "Debounce" logic. Finds an element, waits (`check_interval`), and re-checks `is_enabled()` to prevent `StaleElementReferenceException` caused by page reflows (common in Lark's Flutter/Hybrid views).
  - `click_button_in_punch_card`: Uses Relative Locators (XPath axes). Finds the target button by looking for a sibling "Tip" element (e.g., "应上班 09:00") to ensure the correct card is clicked.
  - `check_time_tip_presence`: Detects the time-tip text to decide if an evening punch is needed.
  - `write_punch_state` / `read_punch_state`: Persist and read the daily decision from the state file.
  - `ensure_icloud_file_synced`: Synchronizes iCloud file to local. Executes `brctl download` to trigger download, then polls file size every 10s until stable (2 consecutive identical sizes).
  - `should_skip_today`: Reads the skip dates file from iCloud, logs its content, and checks if today's date (YYYY-MM-DD) is in the list. Returns `True` to skip punch if matched.

- `config.py` (Configuration):
  - Stores all Selectors (XPaths, IDs), Package names, Activity names, and Business Text (e.g., "上班打卡", "应上班").
  - `STATE_FILE_PATH` controls where the daily punch state is stored.
  - `SKIP_DATES_FILE` specifies the absolute path to the iCloud-synced skip dates file (each line contains a date in YYYY-MM-DD format).
  - `SCREENSHOT_DIR` specifies the directory where failure screenshots are saved.
  - Rule: No hardcoded strings in `main.py`.

- `punch_state.json` (State):
  - Stores the daily decision for whether evening punch is required.

- `lark-punch/` (Skill Package):
  - A standalone Agent Skill directory intended to be published/copied to an external agent's skills path (e.g., `~/.openclaw/workspace/skills/lark-punch/`).
  - `lark-punch/SKILL.md`: Defines the skill. Triggered when the user says「飞书打卡」、「帮我打卡」、「lark 打卡」or「clock in」. Instructs the agent to execute `exec.sh` and return the full log output to the user.
  - This directory is **not** used by the project itself; it only lives here as the source of truth.

- `sync-skills.sh` (Skill Sync Tool):
  - Syncs the `lark-punch/` skill between this project and the openclaw skills directory (`~/.openclaw/workspace/skills`).
  - `--goto`: Pushes local `lark-punch/` to openclaw (overwrites remote).
  - `--sync`: Pulls `lark-punch/` back from openclaw into this project (overwrites local).

- `run.sh` (Cron Wrapper):
  - Cron entry point only. Does NOT load environment or execute Python directly.
  - Logs the cron wake-up time to `run.log`.
  - Implements Anti-Detection: Calculates a random delay (0-180s) before execution.
  - Calls `exec.sh` (absolute path) after the delay — no output redirection here, since `exec.sh` handles its own dual-output logging internally.
  - Triggered by Crontab.

- `screenshots/` (Failure Evidence):
  - Auto-created directory. Contains timestamped PNGs saved by `save_screenshot` on element timeout, instability, click failure, or global exception.

## 4. Coding Guidelines & Best Practices

**Stability First**
  - Never use raw `driver.find_element(...).click()`. Always use `utils.click_element()` or `utils.wait_for_stable_element()`.
  - We prioritize Stability over Speed. Explicit waits and stability checks are mandatory.

**Logging**
  - Use the `logger` object configured in `utils.py`.
  - Format: `logger.info("... message ...")` or `logger.error(f"... {e}")`.
  - Do not use `print()`.

**ADB & Device Handling**
  - Assume the device might be in "Charge Only" mode due to Xiaomi's security settings.
  - The script must be resilient to USB disconnections. Prefer Wireless ADB logic if physical connection fails consistently.
  - Do not leave zombie Appium processes; allow the script to reuse existing processes if healthy.

**Selector Strategy**
  - Lark uses a mix of Native and Web/Flutter views.
  - Preferred Selector: `//android.widget.TextView[@text="..."]` or Resource ID.
  - Complex Scenarios: Use XPath axes (`/..`, `/following-sibling::`) to locate elements relative to stable text anchors.

## 5. Known Issues & Workarounds

  - StaleElementReference: Solved by `wait_for_stable_element` in `utils.py`.
  - Environment Variables: Crontab does not load `.zshrc` by default, so `exec.sh` explicitly sources it and uses absolute paths for Python/Appium. `run.sh` only handles cron scheduling and delegates execution to `exec.sh`.
  - Xiaomi USB Mode: If USB defaults to "Charge Only", the script attempts Wireless connect or relies on phone-side automation (MacroDroid) to auto-click "File Transfer".
  - Xiaomi USB Install Restriction: MIUI may automatically revoke the "USB安装" (Install via USB) Developer Option permission. When this happens, Appium fails with `INSTALL_FAILED_USER_RESTRICTED` while trying to install helper APKs. `init_driver()` handles this automatically by retrying with `skip_server_installation` + `skip_device_initialization`. To permanently fix, re-enable "USB安装" in 设置 → 更多设置 → 开发者选项.
  - Evening skip logic: If the morning time-tip was not found, the evening run exits early based on the recorded state.
  - Skip dates file: The script reads from an iCloud-synced file. If the file is not synced yet, `brctl download` triggers the download, then waits up to 60s for the file size to stabilize before reading. The file content is logged for debugging purposes.