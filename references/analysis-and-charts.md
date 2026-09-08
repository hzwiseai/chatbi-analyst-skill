# 分析与图表

Skill 负责理解问题、选择分析步骤、解释证据和展示结果；服务器提供授权查数、
分析规划器和图表生成器。常见路径如下：

- “有多少用户”：查询聚合总数，给出指标卡与统计口径。
- “最近半年用户增长如何”：按月统计新增用户，使用折线图，说明趋势和异常。
- “用户下降的原因”：使用分析任务比较前后时期，分渠道或用户群体进一步查询，
  用贡献分解验证假设，区分已验证驱动因素与仍需其他证据的解释。

## 调用与展示

以实际 list-tools 返回的工具为准。服务器升级后才有 generate_chart；不存在时
明确说明服务器缺少工具，不能编造结果或通过原始数据库连接绕过。

1. 通过 text2sql 获取需要的聚合数据和 result_id；预览只有前 100 行时不要
   用预览重新计算总体指标。
2. 调用 generate_chart，服务端从完整的已物化结果（受查询上限约束）生成图表，
   并重新校验会话、组织开关、数据源和数据权限。
3. 保存响应 JSON，再渲染为 HTML。例如在 Skill 根目录，替换真实结果 ID：

```bash
python scripts/chatbi_client.py call generate_chart --args-json '{"result_id":"实际结果ID","chart_type":"line","title":"每月新增用户"}' > workspace/user-growth-chart.json
python scripts/render_chart.py --input workspace/user-growth-chart.json --output workspace/user-growth.html
```

HTML 内嵌 ECharts，不依赖 CDN，不访问网络。支持悬停查看、图例切换，普通图表
可下载 PNG；表格和指标卡以 HTML 展示。渲染器拒绝覆盖已有输出文件。
宿主支持文件预览时打开 HTML，否则交付文件链接，并在对话中给出主要结论。

## 分析任务

复杂问题调用 start_analysis，问题中说明目标、时间范围、维度和对比基准。
get_analysis 返回 completed 后，阅读 report、evidence 和 charts；失败、
取消或等待澄清时不要将部分结果表述为最终结论。
完成结果至多附带前四个查询结果的自动图表。需要其他图表时，对 evidence
中的 result_id 单独调用 generate_chart。可将完成的 get_analysis 响应交给
同一渲染脚本，生成包含报告和多图的 HTML。

## 图表选择与核对

| 数据与问题 | chart_type |
|---|---|
| 单个总数或单个指标 | kpi（auto 也会识别） |
| 多个汇总指标 | kpi-group |
| 随时间变化 | line / area |
| 分类比较 | bar |
| 少量非负类别的总体占比 | pie |
| 两个数值变量的关系 | scatter |
| 需要准确查阅明细 | table |

auto 复用系统现有规则；单行数值结果通常优先显示为指标卡。图表不会自动新增
查询维度：只有用户总数时，不能画出月份增长趋势，需先执行对应的聚合查询。
渲染器显示配置所含的结果，指标解释仍需依据实际口径，不凭字段名猜测币种、
单位或状态含义。

核对图表轴、系列、分组顺序、缺失值和单位是否与问题一致；truncated 表示
结果可能不完整，不能把部分分类的饼图当作整体占比。COUNT 无 GROUP BY 的
单行聚合即使因 max_rows=1 被标记 truncated，也应根据 SQL 判断其统计范围，
不能将 returned_rows=1 误认为只有一个用户。最终结论标明 result_id / run_id、
查询时间和权限范围；相关性不等于因果关系。
