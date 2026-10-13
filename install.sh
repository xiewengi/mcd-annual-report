#!/usr/bin/env bash
# ============================================================
# 麦门年度体检报告 · WorkBuddy Skill 一键安装脚本
# 用法：
#   chmod +x install.sh
#   ./install.sh
# ============================================================

set -e

# ====== 路径定义 ======
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="$REPO_ROOT/skills/mcd-annual-report"
SKILLS_DIR="${HOME}/.workbuddy/skills"
SKILL_DST="$SKILLS_DIR/mcd-annual-report"

echo ""
echo "🍔 麦门年度体检报告 · 安装程序"
echo "================================"
echo ""

# ====== 检查源文件 ======
if [ ! -d "$SKILL_SRC" ]; then
  echo "❌ 错误：找不到 skills/mcd-annual-report 目录"
  echo "请确认你在仓库根目录运行本脚本"
  exit 1
fi

if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  echo "❌ 错误：SKILL.md 不存在"
  exit 1
fi

# ====== 创建目录 ======
mkdir -p "$SKILLS_DIR"

# ====== 备份已存在的同名 Skill ======
if [ -d "$SKILL_DST" ]; then
  BACKUP="${SKILL_DST}._bak_$(date +%Y%m%d_%H%M%S)"
  echo "⚠️  检测到已存在的同名 Skill，备份到 $BACKUP"
  mv "$SKILL_DST" "$BACKUP"
fi

# ====== 复制 Skill 文件 ======
cp -r "$SKILL_SRC" "$SKILL_DST"

echo "✅ Skill 已安装到：$SKILL_DST"
echo ""

# ====== 提示 MCP 连接器配置 ======
echo "📋 下一步：配置 MCP 连接器"
echo "--------------------------------"
echo "1. 到 https://open.mcd.cn/mcp 申请 MCP Token（手机号登录即可）"
echo ""
echo "2. 在 WorkBuddy 里配置连接器："
echo "   左侧边栏【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置 MCP】"
echo "   填入 mcd-config.example.json 的内容，把 \${MCD_MCP_TOKEN} 替换为你的真实 Token"
echo ""
echo "3. 或者用环境变量："
echo "   export MCD_MCP_TOKEN='你的真实Token'"
echo ""

# ====== 验证 ======
echo "🔍 验证：运行示例数据"
echo "--------------------------------"
cd "$REPO_ROOT"
python3 generate_report.py --use-sample --save-json 2>&1 | tail -5

echo ""
echo "✅ 安装完成！打开 WorkBuddy，说「帮我生成麦门年度报告」就能用了。"
echo ""
