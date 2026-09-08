# 工具合同 v1

以服务端 `list-tools` 返回的 JSON Schema 为准。所有工具的用户身份由连接
传输凭据确定，不传 user_id、org_id、数据库账号或会话秘密。

| 工具 | 行为 |
|---|---|
| get_connection_info | 身份、版本、限额和原始 SQL 能力 |
| list_resources | 可访问 Agent/数据源分页，cursor 为非负偏移 |
| get_semantic_context | 授权表列及类型，隐藏拒绝/脱敏列 |
| text2sql | question + request_id，mode 为 execute 或 generate |
| execute_query | query_id 或 sql 二选一，request_id；原始 SQL 需额外权限 |
| get_query_result | result_id + cursor + page_size，不重复执行 SQL |
| generate_chart | result_id + chart_type + title，复用系统图表生成器，返回图表配置及查询依据，不重跑 SQL |
| start_analysis | question + request_id；返回 run_id |
| get_analysis | run_id；queued/running/completed/failed/needs_clarification/cancelled |
| resume_analysis | run_id + clarification + request_id；返回新 run_id 和 resumes_run_id |
| cancel_analysis | run_id；cancel_requested 表示执行器尚未确认停止 |

多资源时传 agent_id，或有直接数据源访问权限时传 database_id。SQL 仅支持
MySQL/SQL Server 的单个 SELECT 和基础表 JOIN；CTE、子查询、UNION、未知函数
会拒绝。脱敏列的直接输出变为 NULL，复杂表达式拒绝。LIMIT/TOP 在服务器
强制约束；原有行数限制会保留更小值。结果达到行数上限时 truncated 为 true，
表示可能存在更多数据，不表示服务器已计算精确总数。

SQL 展示省略内部注入的行策略值，数据库实际执行语句由服务器内部保留。
结果与生成的 query_id 有 TTL；读取时权限或策略已改变会拒绝。
`RESULT_POLICY_CHANGED` 需要按新权限重新查询；`REQUEST_ALREADY_ACCEPTED`
不允许以新 ID 自动重放。错误响应不包含原始数据库异常。

新版 MCP 在 isError=true 时提供结构化错误：code、trace_id，以及可用时的
stage、function、executed、generation_attempts。先读取这些字段再决定下一步，
不要围绕同一失败反复改写日期函数尝试。trace_id 可与服务端日志对应。
SQL 校验版本 2 支持 AND/OR、条件聚合、YEAR/MONTH/EXTRACT 和 DATE_FORMAT；
以 get_connection_info 的 mcp_sql_guard_version 确认服务器是否已升级。
服务端只对部分生成 SQL 的校验失败在执行前尝试一次改写，原问题不变，仍走
全部权限与 AST 校验；对权限拒绝、数据库执行错误或不确定结果不自动重试。
