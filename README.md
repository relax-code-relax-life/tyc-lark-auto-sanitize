# 📅 Lark Auto Attendance

这是一个基于 **Appium + Python** 的安卓端飞书自动打卡脚本。

适用于 **macOS (Host)** + **Xiaomi/Android (Device)** 环境。

1. 上班：点击 "打卡" 按钮(适配节假日/请假)
2. 下班：打开飞书“极速打卡“，通过打开飞书后触发极速打卡
3. 如果上班未打卡，则跳过下班打卡
4. 在`~/Library/Mobile\ Documents/iCloud\~md\~obsidian/Documents/iphone-obsidian-vault/clock-in-skip.md`中添加跳过打卡的日期（格式：YYYY-MM-DD），当天不进行打卡操作

---

## 📂 目录结构

确保你的项目包含以下文件：

```text
lark_auto/
├── main.py         # 主程序：逻辑入口，判断早晚打卡模式
├── utils.py        # 工具箱：包含ADB重连、Appium管理、稳定元素查找
├── config.py       # 配置文件：XPath、文案、包名等配置
├── run.sh          # 启动脚本：配置环境变量、随机延迟、启动Python
├── run.log         # 日志文件（运行时自动生成）
└── README.md       # 本文档

```

---

## 🛠 第一步：基础环境安装 (macOS)

在新电脑上，打开终端 (Terminal)，按顺序执行以下命令。

### 1. 安装 Homebrew (如果已有可跳过)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

```

### 2. 安装 Node.js & ADB 工具

Appium 依赖 Node.js，ADB 用于连接手机。

```bash
brew install node
brew install android-platform-tools

```

### 3. 安装 Appium Server

```bash
npm install -g appium

```

### 4. 安装 Appium UiAutomator2 Driver

这是安卓自动化的核心驱动。

```bash
appium driver install uiautomator2

```

---

## 🐍 第二步：Python 环境配置

建议使用 **Conda** 管理环境，避免污染系统 Python。

### 1. 安装 Miniconda

去 [Miniconda官网](https://docs.conda.io/en/latest/miniconda.html) 下载 macOS 对应版本（M1/M2芯片选 Apple Silicon，Intel芯片选 Intel）并安装。

### 2. 创建并激活环境

```bash
# 创建名为 lark_auto 的环境，指定 python 3.10
conda create -n lark_auto python=3.10

# 激活环境
conda activate lark_auto

```

### 3. 安装依赖库

```bash
pip install -r requirements.txt
```

---

## 📱 第三步：手机端设置 (关键！)

**针对小米/红米手机的特殊配置：**

1. **开启开发者模式：** 设置 -> 我的设备 -> 全部参数 -> 连续点击“MIUI版本”或“OS版本”直至开启。
2. **开启 USB 调试：** 设置 -> 更多设置 -> 开发者选项 -> 开启 **【USB调试】**。
3. **开启 USB 调试 (安全设置)：** 必须开启！(需要插卡并登录小米账号)，否则无法模拟点击。
4. **修改 USB 默认配置：** 开发者选项 -> 默认 USB 配置 -> 选择 **【文件传输】** (防止充电模式导致断连)。
5. **允许后台运行：** 锁定飞书 App 后台，防止被杀后台导致冷启动过慢。

---

## ⚙️ 第四步：项目配置

### 1. 获取绝对路径

在终端（确保已激活 `lark_auto` 环境）执行：

```bash
# 获取 Python 解释器路径
which python
# 示例输出: /Users/yourname/miniconda3/envs/lark_auto/bin/python

# 获取项目所在路径
pwd
# 示例输出: /Users/yourname/Documents/lark_auto

```

### 2. 修改 `run.sh`

用文本编辑器打开 `run.sh`，**必须修改**以下两处为上一步获取的真实路径：

```bash
#!/bin/zsh
# ... (环境变量部分保持不变)

# 👇 修改 1: 项目目录
cd /Users/yourname/Documents/lark_auto 

# ... (随机延迟逻辑保持不变)

# 👇 修改 2: Python 解释器路径
/Users/yourname/miniconda3/envs/lark_auto/bin/python main.py >> run.log 2>&1

```

### 3. 赋予执行权限

```bash
chmod +x run.sh
```

---

## ⏰ 第五步：定时任务 (Crontab)

配置自动化触发，无需人工干预。

### 1. 授予磁盘权限 (Mac 必做)

打开 **系统设置** -> **隐私与安全性** -> **完全磁盘访问权限 (Full Disk Access)**。
点击 `+` 号，添加 `/usr/sbin/cron` (如果找不到，至少添加 **终端(Terminal)**)。

### 2. 编辑 Crontab

在终端执行：

```bash
crontab -e

```

### 3. 写入配置

按下 `i` 进入编辑模式，粘贴以下内容（注意修改 `run.sh` 的路径）：

```cron
# 上班打卡：每天 09:25 触发 (脚本内含 0~3分钟随机延迟)
25 09 * * * /Users/yourname/Documents/lark_auto/run.sh

# 下班打卡：每天 19:10 触发 (执行等待逻辑，假装下班)
10 19 * * * /Users/yourname/Documents/lark_auto/run.sh

```

按下 `Esc`，输入 `:wq` 保存退出。

---

## 🔋 第六步：电源管理 (防休眠)

为了保证脚本运行时 Mac 的 USB 端口供电正常：

1. 打开 **系统设置** -> **显示器** -> **高级** (或“节能”)。
2. 开启 **“防止计算机在显示器关闭时自动进入睡眠”**。
3. 或者保持 Mac Mini 常亮不关机。

---

## 🚀 验证与测试

### 1. 手动测试脚本

在终端直接运行：

```bash
./run.sh
```

观察 `run.log` 是否生成，手机是否自动打开飞书并进行操作。

### 2. 验证 Appium & ADB

如果报错，检查日志。

* `check_and_start_appium`: 会自动拉起 Appium 服务。
* `ensure_adb_connected`: 如果 USB 断连，会自动尝试重启 ADB 或 Wi-Fi 重连 (需在 utils.py 配置 IP)。

---

## ❓ 常见问题 (Troubleshooting)

**Q: 报错 `Could not find a connected Android device**`

* **A:** 检查手机 USB 是否变成了“仅充电”。
* 拔插数据线，选择“文件传输”。
* 或者配置 `utils.py` 使用无线 ADB (`adb connect IP:5555`)。



**Q: 报错 `StaleElementReferenceException**`

* **A:** 忽略即可。`utils.py` 中的 `wait_for_stable_element` 会自动处理页面刷新导致的元素失效问题。

**Q: 早上 09:25 没反应？**

* **A:** 检查 Mac 是否休眠了。检查 Crontab 是否配置正确。查看 `run.log` 是否有启动记录。

**Q: 提示 `bindkey: command not found` 邮件？**

* **A:** 确保 `run.sh` 第一行是 `#!/bin/zsh` 而不是 `#!/bin/bash`。