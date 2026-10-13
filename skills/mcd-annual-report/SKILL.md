# 🍔 麦门年度体检报告 (mcd-annual-report)

> 基于麦当劳中国官方 MCP，拉取你的全部历史订单，生成一份"反向体检报告"——从营养匹配、热量分析、健康评分到麦门人设，一键搞定。

---

## 触发词

以下任意表达都会启动本 Skill：

- "我的麦当劳年报" / "麦门年度报告" / "帮我分析麦当劳订单"
- "我今年吃了多少麦当劳" / "麦当劳消费分析"
- "我的麦门人设是什么" / "麦当劳健康评分"
- "麦门体检" / "麦当劳年度总结"

---

## 前置条件

1. **麦当劳 MCP Token**：用户需先到 <https://open.mcd.cn/mcp> 手机号登录 → 控制台 → 一键复制 Token
2. **MCP 连接器**：用户需在 WorkBuddy 里配置好 `mcp.mcd.cn` 连接器（模板见 `mcd-config.example.json`）
3. **Python 3.7+**：脚本运行依赖，标准库零外部包

---

## 执行步骤

按以下顺序调用麦当劳 MCP 工具：

### Step 1 · 确认 Token 就绪

```
调用方：mcp.mcd.cn
工具：initialize
预期：返回 serverInfo（version、capabilities 等）
```

如果 initialize 失败（401 / 403），提示用户检查 Token 是否正确。

### Step 2 · 拉取历史订单

```
调用方：mcp.mcd.cn
工具：order-list
参数：{}（无参数拉全部）
预期：返回 list 数组，每项包含 orderId、createTime、orderProductList、storeName、realTotalAmount 等
```

### Step 3 · 拉取营养表

```
调用方：mcp.mcd.cn
工具：list-nutrition-foods
参数：{}
预期：返回 CSV 格式文本，列为 productName, description, energy_kj, energy_kcal, protein, fat, carbohydrate, sodium, calcium
```

### Step 4 · 本地运行分析脚本

在仓库根目录执行：

```bash
python3 generate_report.py \
  --token "{用户的 MCP Token}" \
  --output output/annual_report.html \
  --save-json
```

或者如果用户想先看示例效果：

```bash
python3 generate_report.py --use-sample --save-json
```

### Step 5 · 向用户展示结果

脚本执行完成后，向用户：

1. **复述核心结论**（用自然语言，不是 raw JSON）：
   - "你过去一年点了 **N 单**麦当劳，总共花了 **¥XXX**"
   - "健康评分 **XX 分**，属于「**麦门健康达人**」"
   - "你的麦门人设是「**脆皮鸡肉爱好者 🍗**」"
   - "营养数据匹配率 **XX%**，其中精确匹配 XX 项、模糊匹配 XX 项"
2. **展示 HTML 报告路径**，提示可直接打开浏览器查看
3. **询问是否要保存人格卡**（后续扩展）

---

## 报告包含的内容

| 板块 | 说明 |
|---|---|
| 📊 年度总览 | 订单数、消费总额、每周频次、营养匹配率 |
| 🔍 数据可信度 | 精确/模糊/包含/估算 四级匹配分布条 |
| ❤️ 健康评分 | 热量/钠/蛋白质/脂肪四维度 + 百分制综合评级 |
| 🎭 麦门人设 | 16 种角色自动判定 + emoji + 消费画像拆解 |
| 🔥 热量画像 | 平均/最高/最低单餐 + 各餐段与推荐区间对比 |
| 📅 餐段分布 | 早/午/下午茶/晚/宵夜 频次柱状图 |
| 📈 月度趋势 | 12 个月柱状图 + 详细表格 |
| ⭐ Top 15 最爱 | 高频商品排行榜 |
| ✨ 年度高光 | 最热月、最贵一餐、热量巅峰等 |
| 🥗 营养总量 | 年度热量/蛋白质/脂肪/钠总和 |
| 📝 订单明细 | 全部历史订单一览表 |

---

## 安全红线（必须遵守）

1. **只读操作**：本 Skill 只调用 `order-list` 和 `list-nutrition-foods` 两个只读工具
2. **绝不调用**：`create-order`、`cancel-order`、`auto-bind-coupons`、`draw-lottery` 等写操作
3. **Token 不回显**：用户贴的 Token 只用于本次会话连接，**绝不在回复里原样输出**
4. **不上传任何数据**：所有分析在本地完成，生成的 HTML/JSON 文件只存于本机
5. **每分钟 600 次**：遵守 MCP 平台限流，脚本内部已做简单节流

---

## 技术实现

- **MCP 客户端**：纯 Python 3 标准库（`urllib`）实现 Streamable HTTP 协议
- **分析引擎**：`analyzer.py` 包含营养匹配、健康评估、人设判定、年度高光等模块
- **报告生成**：`generate_report.py` 用单文件 HTML 模板 + Python `str.replace` 渲染，零外部依赖
- **离线可用**：`--use-sample` 内置示例订单数据，无 Token 也能跑通全流程

---

## 参赛信息

- **大赛**：2026 麦当劳程序员创意开发大赛 · WorkBuddy × 麦当劳
- **方向**：反向分析类作品——不是"今天吃什么"，而是"你这一年吃了什么"
- **官方 MCP**：<https://mcp.mcd.cn>
- **仓库**：待填写（clone 后改为你自己的 GitHub 地址）
