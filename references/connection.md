# 安装与连接

本组织系统管理员需在“系统设置 → MCP 服务”开启服务并选择允许的数据源。
用户只提供 ChatBI 账号密码；服务器自动签发会话，不需要另外配置 MCP 密钥。
收到 `MCP_DISABLED` 时说明所属组织尚未开通或已关闭；设置变更导致 `SESSION_REVOKED`
时重启客户端以重新登录，不通过修改客户端绕过开关。

安装源码客户端：`python -m pip install /path/to/integrations/chatbi-mcp`。
发布 ZIP 解压后：`python -m pip install -r scripts/requirements.txt`，随后通过
`python scripts/chatbi_client.py` 使用相同的子命令。

也可以直接使用 Skill 自带的 `.env.example`。在 Skill 目录下运行：

```bash
python -m pip install -r scripts/requirements.txt
cp .env.example .env  # 仅首次配置，已有 .env 时保留
chmod 600 .env
# 在本地编辑 .env，填写 CHATBI_SERVER_URL、CHATBI_USERNAME、CHATBI_PASSWORD
python scripts/chatbi_client.py doctor
python scripts/chatbi_client.py list-tools
python scripts/chatbi_client.py serve --transport stdio
```

随包客户端自动读取与 SKILL.md 同目录的 `.env`，不受启动工作目录影响。
独立安装的 `chatbi-mcp` 可用 `CHATBI_ENV_FILE` 指定该文件路径。配置优先级为
进程环境变量 > `.env` > configure 保存的本地配置。使用 `.env` 时无需
再运行 configure；configure 不修改 `.env`，切换配置方式时注意上述优先级。
密码作为文本读取，不执行 shell，也不展开 `${...}`。真实 `.env` 不提交、不打包。

用户在自己的终端运行 `chatbi-mcp configure`，仅输入服务器根地址、ChatBI
用户名、密码。密码隐藏输入并保存到用户配置目录的 config.json（文件权限 0600），配置不属于 Skill 内容。
本地服务使用 `http://localhost:5390`，配置器地址直接回车即可。
完整 MCP 端点为 `http://localhost:5390/mcp/chatbi`；配置器填根地址，
不要附加 `/mcp/chatbi`。本地端口指客户端所在机器；远程使用需填可达的服务地址。
环境注入也支持 CHATBI_SERVER_URL、CHATBI_USERNAME、CHATBI_PASSWORD；桌面
宿主不保证继承终端环境，优先使用配置器。

原生 MCP 宿主注册本地命令 `chatbi-mcp serve --transport stdio`。注册格式
取决于宿主，固定命令必须使用实际安装的绝对路径。仅有远程 URL 不能完成
当前自有认证流程；标准远程 OAuth 尚未实现。

有脚本执行能力时，可调用 `chatbi-mcp list-tools` 或
`chatbi-mcp call list_resources --args-json '{}'`。
`chatbi-mcp doctor` 检查连接。客户端不调用系统钥匙串，MCP 会话只在当前
客户端进程内缓存。单独启动的命令会重新登录；常驻 stdio 客户端在有效期内复用
会话。`disconnect` 只撤销当前客户端实例持有的会话；新进程没有可撤销的旧
会话，会返回 no_active_session，不会为了退出而新建会话。已结束进程的会话
由服务器到期清理；组织设置变更仍可令该组织的旧会话失效。
认证失败后重新 configure，不向对话提供密码。
