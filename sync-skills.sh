#!/bin/zsh

# ==========================================
# README:
# 同步 lark-punch skill 到 openclaw 或从 openclaw 拉回本项目
#
# 用法:
#   ./sync-skills.sh --goto   将本项目 lark-punch/ 推送到 openclaw skills 目录
#   ./sync-skills.sh --sync   从 openclaw skills 目录拉回 lark-punch/ 到本项目（覆盖）
# ==========================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_SKILL="$SCRIPT_DIR/lark-punch"
REMOTE_SKILLS_DIR="/Users/wangwl.net/.openclaw/workspace/skills"
REMOTE_SKILL="$REMOTE_SKILLS_DIR/lark-punch"

case "$1" in
  --goto)
    echo "📤 推送 lark-punch → $REMOTE_SKILLS_DIR"
    mkdir -p "$REMOTE_SKILLS_DIR"
    cp -r "$LOCAL_SKILL" "$REMOTE_SKILLS_DIR/"
    echo "✅ 完成：$REMOTE_SKILL"
    ;;
  --sync)
    echo "📥 拉取 $REMOTE_SKILL → $SCRIPT_DIR"
    if [[ ! -d "$REMOTE_SKILL" ]]; then
      echo "❌ 远端目录不存在：$REMOTE_SKILL"
      exit 1
    fi
    rm -rf "$LOCAL_SKILL"
    cp -r "$REMOTE_SKILL" "$SCRIPT_DIR/"
    echo "✅ 完成：$LOCAL_SKILL"
    ;;
  *)
    echo "用法: $0 --goto | --sync"
    echo "  --goto   将本项目 lark-punch/ 推送到 openclaw skills 目录"
    echo "  --sync   从 openclaw skills 目录拉回 lark-punch/ 到本项目（覆盖）"
    exit 1
    ;;
esac
