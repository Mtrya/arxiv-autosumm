# Troubleshooting & Q&A

This document provides solutions to common issues and answers frequently asked questions.

## Known Limitations

- **Rate Limiting**: Some LLM providers have aggressive rate limits. If you encounter repeated API errors, you may need to adjust your request frequency or consider a different provider.
- **VLM Parsing**: Enabling VLM parsing can be time-consuming and expensive, especially for long papers with many figures. The quality of the output depends heavily on the specific model and prompts used. It is an advanced feature and may require experimentation to get right.
- **Processing Time**: Summarizing a large batch of papers can take a significant amount of time, depending on the models, rating strategies, and number of papers you've configured.

## Frequently Asked Questions (FAQ)

*(This section can be expanded with common user questions.)*

**Q: Why are my emails not being delivered?**

A: Check your SMTP settings in `config.yaml` or your repository secrets. Ensure the server, port, email, and password are correct. Some email providers, like Gmail, may require you to use an "App Password" instead of your regular login password.

**Q: How can I add a new LLM provider?**

A: You can add a custom provider by specifying its `base_url` and `model` in your `config.yaml`. If the provider is not one of the recognized names, you will need to provide the full `base_url` configuration.
