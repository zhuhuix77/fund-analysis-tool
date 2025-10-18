# 基金监控应用云端部署指南

本文档将指导您如何将本应用安全、免费地部署到云端，实现网站的公开访问和后台监控任务的自动化运行。

## 部署架构

我们将采用“网站与任务分离”的方案：

1.  **前端网站 (`app.py`)**: 部署在 **Streamlit Community Cloud** 上，提供交互界面。
2.  **后台监控 (`monitor.py`)**: 通过 **GitHub Actions** 的定时任务 (Cron Job) 自动运行，负责发送邮件提醒。
3.  **机密信息管理**: 您的邮箱密码、GitHub 令牌等敏感信息，将分别存储在 Streamlit 和 GitHub 各自的 **Secrets**（云端保险箱）中，**绝不会**出现在公开的代码库里。

---

## 部署步骤

### 第 1 步：在 GitHub 上创建个人访问令牌 (PAT)

这是为了授权 `app.py` 网站能够修改您代码库中的 `fund_strategies.json` 文件。

1.  登录您的 GitHub 账户。
2.  点击右上角头像 -> **Settings**。
3.  在左侧菜单最下方，选择 **<> Developer settings**。
4.  选择 **Personal access tokens** -> **Tokens (classic)**。
5.  点击 **Generate new token** -> **Generate new token (classic)**。
6.  **Note**: 给令牌起一个描述性的名字，例如 `STREAMLIT_FUND_APP_SYNC`。
7.  **Expiration**: 建议选择 `No expiration`（无过期时间），或者一个较长的时间。
8.  **Select scopes**: **最关键的一步**，勾选 `repo` 这个顶级复选框。这将授予令牌读写代码库的全部权限。
9.  点击页面最下方的 **Generate token**。
10. **立即复制生成的令牌！** 这个令牌只会显示一次，请将其复制到一个安全的地方，我们马上会用到。

### 第 2 步：在 GitHub 仓库中设置 Secrets

这是为了让 `monitor.py` 在 GitHub Actions 上运行时，能够获取到您的邮箱配置。

1.  打开您这个项目所在的 GitHub 仓库页面。
2.  点击上方的 **Settings** 标签页。
3.  在左侧菜单中，选择 **Secrets and variables** -> **Actions**。
4.  确保您在 **Secrets** 标签页下，然后点击 **New repository secret**。
5.  您需要**逐一**添加以下 **5 个** Secret：

| Secret 名称 (Name) | 您的值 (Value) | 说明 |
| :--- | :--- | :--- |
| `SENDER_EMAIL` | `your_name@163.com` | 您的发件人邮箱地址 |
| `EMAIL_PASSWORD` | `xxxxxxxxxxxxxx` | 您的邮箱**授权码** (非登录密码) |
| `RECEIVER_EMAILS`| `receive@qq.com` | 您的收件人邮箱地址 |
| `SMTP_SERVER` | `smtp.163.com` | 您的发件箱 SMTP 服务器地址 |
| `SMTP_PORT` | `465` | 您的发件箱 SMTP SSL 端口 |

**注意**: `RECEIVER_EMAILS` 如果有多个，目前这里只支持填写一个。

### 第 3 步：在 Streamlit Cloud 上部署并设置 Secrets

这是为了让 `app.py` 网站能够运行，并有权限连接到 GitHub。

1.  登录您的 [Streamlit Community Cloud](https://share.streamlit.io/) 账户。
2.  点击 **New app** -> **From GitHub**。
3.  选择您这个项目所在的仓库和分支。
4.  在 **Advanced settings...** 中，选择与您本地环境匹配的 Python 版本。
5.  点击 **Deploy!**，等待应用首次部署。
6.  首次部署可能会因为缺少 Secrets 而报错，这是正常的。部署完成后，进入应用的设置页面（点击右下角的 `Manage app`）。
7.  在 **Settings** -> **Secrets** 中，粘贴以下内容：

    ```toml
    # 1. GitHub 配置 (用于同步策略文件)
    GITHUB_REPO_NAME = "your_username/your_repo_name"
    GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # 2. 邮箱配置 (仅用于 app.py 中的测试功能，与 GitHub Actions 无关)
    # 注意：这里的邮箱配置与 GitHub Secrets 中的内容是重复的，
    # 这是因为 Streamlit 和 GitHub Actions 是两个独立的环境。
    SENDER_EMAIL = "your_name@163.com"
    EMAIL_PASSWORD = "xxxxxxxxxxxxxx"
    RECEIVER_EMAILS = "receive@qq.com"
    SMTP_SERVER = "smtp.163.com"
    SMTP_PORT = 465
    ```

8.  **请将上述内容中的值替换为您自己的真实信息**：
    *   `GITHUB_REPO_NAME`: 您的 GitHub 用户名和仓库名，例如 `my-username/my-fund-app`。
    *   `GITHUB_TOKEN`: 您在**第 1 步**中创建并复制的个人访问令牌。
    *   其余邮箱信息：与您在**第 2 步**中填入 GitHub Secrets 的内容保持一致。
9.  点击 **Save**。Streamlit 会自动重启您的应用。

---

## 部署完成！

现在，您的整个系统已经完全部署在云端：

*   您可以随时访问您的 Streamlit 网站 (`app.py`)。
*   当您在网站上添加或删除监控策略时，更改会自动同步到 GitHub 上的 `fund_strategies.json` 文件。
*   GitHub Actions 会在每个交易日的 14:45 自动运行，拉取最新的策略文件，并使用您存在 GitHub Secrets 中的邮箱配置发送决策报告邮件。

您的所有机密信息都得到了妥善的保护。