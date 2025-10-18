# ArXiv AutoSumm

基于 LLM 的 ArXiv 自动化研究论文摘要工具，提供智能评分、多格式输出和全面的配置管理功能。

[English](README.md) | [中文](README.zh-CN.md)

## 快速开始：GitHub Actions

最快的入门方法是使用 GitHub Actions，它可以自动化整个流程。此方法使用仓库机密动态配置应用程序，无需提交任何配置文件。

**前置条件：**

- GitHub 账号
- 您选择的 LLM 提供商的 API 密钥
- 用于接收摘要的 SMTP 电子邮件帐户

### 步骤

1. **Fork 本仓库**

   点击此页面右上角的“Fork”按钮，在您自己的 GitHub 帐户中创建此存储库的副本。
2. **配置仓库机密**

   导航到您 Fork 的存储库的 **Settings** > **Secrets and variables** > **Actions**。添加以下机密以配置管道。只有 `SUMMARIZER_API_KEY`、`RATER_API_KEY`、`SMTP_SERVER`、`SENDER_EMAIL`、`RECIPIENT_EMAIL` 和 `SMTP_PASSWORD` 是必需的。

   | 机密                    | 必需 | 描述                                                                        |
   | ----------------------- | :--: | --------------------------------------------------------------------------- |
   | `SUMMARIZER_API_KEY`  |  ✅  | 用于摘要 LLM 的 API 密钥。                                                  |
   | `RATER_API_KEY`       |  ✅  | 用于评分 LLM 的 API 密钥。                                                  |
   | `SMTP_SERVER`         |  ✅  | 您电子邮件提供商的 SMTP 服务器 (例如 `smtp.163.com`)。                    |
   | `SENDER_EMAIL`        |  ✅  | 用于发送摘要的电子邮件地址。                                                |
   | `RECIPIENT_EMAIL`     |  ✅  | 用于接收摘要的电子邮件地址。                                                |
   | `SMTP_PASSWORD`       |  ✅  | 您发件人电子邮件的密码或应用密码。                                          |
   | `ARXIV_CATEGORIES`    |  ❌  | 逗号分隔的 ArXiv 类别 (例如,`cs.AI,cs.CV`,默认为 `cs.AI,cs.CV,cs.RO`)。 |
   | `MAX_PAPERS`          |  ❌  | 要摘要的最大论文数 (默认为5)。                                              |
   | `SUMMARIZER_PROVIDER` |  ❌  | 用于摘要的 LLM 提供商 (例如,`openai`,默认为 `modelscope`)。             |
   | `RATER_PROVIDER`      |  ❌  | 用于评分的 LLM 提供商 (例如,`anthropic`,默认为 `modelscope`)。          |

3. **启用并运行工作流**

   - 转到您存储库中的 **Actions** 选项卡。
   - 如果出现提示，请启用工作流。
   - 选择 **ArXiv AutoSumm Daily** 工作流，然后单击 **Run workflow**。

就这样！GitHub工作流现在将按计划运行，每天早上将摘要发送到您的邮箱。有关更高级的设置，包括本地安装和详细配置，请参阅我们的[完整文档](docs/)。

## 功能特性

- **自动化论文处理**：每日自动获取、评分、摘要和交付论文。
- **多种输出格式**：支持 PDF、HTML、Markdown 和 AZW3 (Kindle)。
- **高级缓存**：通过基于 SQLite 的缓存避免重复处理论文。
- **灵活的评分**：可选择 LLM、embedding 或混合评分策略。
- **VLM 解析**：支持配置 VLM 以解析 PDF。

## 工作流概览

工作流按以下顺序处理论文：

1. **获取 (Fetch)**：从 ArXiv 下载论文数据。
2. **评分 (Rate)**：选择最相关/有趣的论文。
3. **解析 (Parse)**：从 PDF 中提取内容。
4. **摘要 (Summarize)**：使用强大的 LLM 生成摘要。
5. **渲染 (Render)**：以您期望的格式创建输出。
6. **投递 (Deliver)**：通过电子邮件将摘要发送给您。

## 📚 文档

- [**安装指南**](docs/INSTALLATION.md)：关于 GitHub Actions 和本地环境的详细设置说明。
- [**配置指南**](docs/CONFIGURATION.md)：所有配置选项的全面参考。
- [**故障排除与问答**](docs/TROUBLESHOOTING.md)：常见问题的解决方案和问答。

## 📄 许可证

本项目基于 MIT 许可证授权 - 详见 [LICENSE](LICENSE) 文件。
