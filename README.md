# ClawChatBI 智能分析 Skill

## 产品介绍

**ClawChatBI 是面向业务场景的智能数据分析平台，让你通过自然语言提问，完成数据查询、指标分析和可视化。**

产品网站：[clawchatbi.com](https://clawchatbi.com)

你可以像与数据分析师交流一样提出问题，例如：

- “本月销售额是多少？与上个月相比有什么变化？”
- “按地区拆分订单，找出增长最快的区域。”
- “分析最近的销售下降原因，生成图表和分析报告。”

ClawChatBI 将业务问题与数据源中的表结构、指标、维度和业务术语结合，生成 SQL 并查询数据，再以图表、指标卡或分析报告呈现结果。平台提供数据源管理、业务语义管理、分析 Agent 和报表等能力，也支持私有化部署。

本 Skill 通过 ChatBI MCP 服务，把这些查询与分析能力接入支持 Skill 和脚本执行的 AI 助手。它使用你的 ChatBI 账号访问获授权的数据源或 Agent，支持查数、多步分析、趋势与异常诊断，以及基于查询结果生成图表和离线 HTML 报告。

实际可用的数据与工具取决于账号权限、组织设置和服务端版本。

## 配置说明：修改 `.env`

### 1. 准备账号与环境

- 准备可登录的 ChatBI 账号，以及管理员提供的 **MCP 服务根地址**。
- 请组织管理员在“系统设置 → MCP 服务”中开启服务，并选择允许使用的数据源。
- 本机安装 Python 3.11 或以上版本。

进入本 Skill 目录，也就是包含 `SKILL.md` 的 `chatbi-analyst/` 文件夹，安装客户端依赖：

```bash
python -m pip install -r scripts/requirements.txt
```

以下命令均在这个文件夹中执行。部分系统的 Python 命令为 `python3`，请相应替换。

### 2. 创建 `.env`

首次使用时，将随包的 `.env.example` 复制一份，命名为 `.env`，与 `SKILL.md` 放在同一目录。如果已经有 `.env`，直接编辑，不要覆盖原配置。

macOS / Linux：

```bash
# 仅在 .env 不存在时复制
[ -f .env ] || cp .env.example .env
chmod 600 .env
```

Windows PowerShell：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

也可以在文件管理器中复制并重命名。注意文件名必须是 `.env`，不能是 `.env.txt`；macOS / Linux 中以点开头的文件可能默认隐藏。

### 3. 填写三个配置项

用本地文本编辑器打开 `.env`，按你的实际账号填写：

```dotenv
# MCP 服务根地址，以管理员提供的地址为准
CHATBI_SERVER_URL=https://clawchatbi.com

# 你的 ChatBI 登录用户名
CHATBI_USERNAME=your-username

# 你的 ChatBI 登录密码
CHATBI_PASSWORD='your-password'
```

| 配置项 | 如何填写 |
| --- | --- |
| `CHATBI_SERVER_URL` | 能从当前电脑访问的 MCP 服务根地址，包含 `http://` 或 `https://`。域名示例仅在该域名已对外提供 MCP 服务时适用；私有化部署填写管理员提供的地址。 |
| `CHATBI_USERNAME` | 你在 ChatBI 中使用的登录用户名，不是数据库用户名。 |
| `CHATBI_PASSWORD` | 对应账号的登录密码，不是数据库密码，也不是模型 API Key。 |

地址不要附加 `/mcp/chatbi`、`/api/mcp/login` 或网页页面路径，客户端会自动拼接接口地址。

如果 MCP 服务就在当前电脑上，并使用默认端口，可以改为：

```dotenv
CHATBI_SERVER_URL=http://localhost:5390
```

如果服务在另一台机器上，需要填写那台机器可访问的域名或 IP 与端口。`localhost` 始终指运行客户端的当前机器。

密码包含空格或 `#` 时，用英文单引号包裹；密码本身包含单引号时可用英文双引号包裹，并按 dotenv 格式转义其中的双引号和反斜杠。客户端将密码作为文本读取，不执行 shell，也不展开 `${...}`。

只在本地填写密码，不把实际 `.env` 发到聊天、提交到 Git 或放进分享包。无需手动填写 Token、会话密钥、Agent ID 或数据库连接信息。

### 4. 检查连接

保存 `.env` 后运行：

```bash
python scripts/chatbi_client.py doctor
python scripts/chatbi_client.py list-tools
```

连接正常后，可以查看当前账号可访问的资源：

```bash
python scripts/chatbi_client.py call list_resources --args-json '{}'
```

随后在已安装本 Skill 的 AI 助手中提出业务问题即可。若宿主需要注册本地 MCP 进程，启动命令为：

```bash
python scripts/chatbi_client.py serve --transport stdio
```

宿主中的 Python 与脚本路径应填写实际绝对路径；具体注册格式由宿主决定。

### 5. 修改配置后如何生效

随包客户端自动定位 Skill 目录中的 `.env`，不依赖启动命令时的工作目录。

修改并保存后，新启动的命令会读取新配置；已经常驻运行的 MCP 客户端需要重启。使用 `.env` 时不必额外运行 `configure`。

配置优先级为：**进程环境变量 > `.env` > `configure` 保存的本地配置**。如果修改 `.env` 后仍连接旧服务，检查宿主或终端是否设置了同名环境变量，以及是否通过 `CHATBI_ENV_FILE` 指定了其他配置文件。

## 常见问题

| 情况 | 处理方式 |
| --- | --- |
| 连接失败 | 核对根地址、端口、网络，以及目标地址是否已提供 MCP 服务。 |
| 认证失败 | 在本地核对用户名和密码，保存后重启客户端。 |
| `MCP_DISABLED` | 请组织管理员开启 MCP 服务并选择数据源。 |
| `SESSION_REVOKED` | 组织配置可能已变更，重启客户端重新登录。 |
| 工具可用但没有目标数据源 | 请管理员检查账号的 Agent / 数据源访问权限和 MCP 允许范围。 |

更多信息：[连接说明](references/connection.md) · [工具合同](references/tools.md) · [分析与图表](references/analysis-and-charts.md) · [工作目录约定](references/workspace.md)。
