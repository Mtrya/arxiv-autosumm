# ArXiv AutoSumm

Automated research paper summarization from ArXiv with LLM-powered rating, multi-format delivery, and comprehensive configuration management.

[English](README.md) | [中文](README.zh-CN.md)

## Quick Start: GitHub Actions

The fastest way to get started is with GitHub Actions, which automates the entire pipeline. This method uses repository secrets to dynamically configure the application without needing to commit any configuration files.

**Prerequisites:**

- A GitHub account
- API keys for your chosen LLM providers
- An SMTP email account for receiving summaries

### Steps

1.  **Fork the Repository**

    Click the "Fork" button at the top-right of this page to create a copy of this repository in your own GitHub account.

2.  **Configure Repository Secrets**

    Navigate to your forked repository's **Settings** > **Secrets and variables** > **Actions**. Add the following secrets to configure the pipeline. Only `SUMMARIZER_API_KEY`, `RATER_API_KEY`, `SMTP_SERVER`, `SENDER_EMAIL`, `RECIPIENT_EMAIL`, and `SMTP_PASSWORD` are strictly required.

    | Secret                | Required | Description                                      |
    | --------------------- | :------: | ------------------------------------------------ |
    | `SUMMARIZER_API_KEY`  |    ✅    | API key for the summarization LLM.               |
    | `RATER_API_KEY`       |    ✅    | API key for the rating LLM.                      |
    | `SMTP_SERVER`         |    ✅    | Your email provider's SMTP server.               |
    | `SENDER_EMAIL`        |    ✅    | The email address for sending summaries.         |
    | `RECIPIENT_EMAIL`     |    ✅    | The email address for receiving summaries.       |
    | `SMTP_PASSWORD`       |    ✅    | The password or app password for your sender email. |
    | `ARXIV_CATEGORIES`    |    ❌    | Comma-separated ArXiv categories (e.g., `cs.AI,cs.CV`). |
    | `MAX_PAPERS`          |    ❌    | The maximum number of papers to summarize.       |
    | `SUMMARIZER_PROVIDER` |    ❌    | The LLM provider for summarization (e.g., `openai`). |
    | `RATER_PROVIDER`      |    ❌    | The LLM provider for rating (e.g., `anthropic`). |

3.  **Enable and Run the Workflow**

    - Go to the **Actions** tab in your repository.
    - If prompted, enable the workflows.
    - Select the **ArXiv AutoSumm Daily** workflow and click **Run workflow**.

That's it! The workflow will now run on its schedule, delivering summaries to your inbox. For more advanced setups, including local installation and detailed configuration, see our [full documentation](docs/).

## Features

- **Automated Paper Processing**: Fetches, rates, summarizes, and delivers papers daily.
- **Multiple Output Formats**: Supports PDF, HTML, Markdown, and AZW3 (Kindle).
- **Advanced Caching**: Avoids re-processing papers with an SQLite-based cache.
- **Flexible Rating**: Choose between LLM, embedding, or hybrid rating strategies.
- **VLM Parsing**: Optional Vision Language Model support for enhanced PDF analysis.

## Pipeline Overview

The pipeline processes papers in the following sequence:

1. **Fetch**: Downloads metadata from ArXiv.
2. **Rate**: Selects the most relevant/interesting papers.
3. **Parse**: Extracts content from the PDFs.
4. **Summarize**: Generates summaries with a powerful LLM.
5. **Render**: Creates outputs in your desired formats.
6. **Deliver**: Sends the summaries to you via email.

## Documentation

- [**Installation Guide**](docs/INSTALLATION.md): Detailed setup instructions for GitHub Actions and local environments.
- [**Configuration Guide**](docs/CONFIGURATION.md): Comprehensive reference for all configuration options.
- [**Troubleshooting & Q&A**](docs/TROUBLESHOOTING.md): Solutions for common issues and frequently asked questions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
