# Configuration Guide

This document provides a comprehensive guide to configuring ArXiv AutoSumm. For a minimal setup, see the Quick Start section in the main `README.md`.

## GitHub Actions Configuration

When running with GitHub Actions, you have two primary methods for providing configuration: repository secrets for quick setup, and a committed `config.yaml` for advanced control.

### Option A: Dynamic Configuration (Secrets)

This is the fastest way to get started. The workflow will automatically generate a configuration file based on secrets you define in your repository settings.

- **How it works**: The `.github/scripts/create-config.sh` script reads pre-defined repository secrets and generates a `config.yaml` at runtime.
- **Best for**: Users who want a simple, secure setup without committing configuration files.

See the [Installation Guide](INSTALLATION.md#option-a-dynamic-configuration-quick-start) for the full list of supported secrets.

### Option B: Repository Configuration (`config.yaml`)

This method gives you full control over all settings, including advanced features like VLM parsing and hybrid rating.

- **How it works**: Set the `USE_REPO_CONFIG` repository variable to `true`. The workflow will then use the `config.yaml` file from your repository.
- **Best for**: Users who need to customize prompts, define complex rating criteria, or enable advanced pipeline features.

#### Environment Variables in `config.yaml`

For security, never commit sensitive data like API keys directly into `config.yaml`. Instead, use environment variables with the `env:` prefix. The workflow will substitute these at runtime.

**Example:**

```yaml
summarize:
  # The workflow will fetch the value of the SUMMARIZER_API_KEY secret
  api_key: env:SUMMARIZER_API_KEY

fetch:
  # The workflow will fetch the value of the FETCH_RESULTS variable
  max_results: env:FETCH_RESULTS
```

#### Secret Naming Constraints

GitHub Actions has technical limitations that prevent workflows from accessing arbitrary secret names dynamically. Because of this, you must use one of the following supported patterns:

1. **Repository Variables**: You can use any name for repository variables (e.g., `MY_MODEL`, `CUSTOM_DAYS`). These are not secrets and are visible in the repository settings.
2. **Pre-defined Secret Names**: A fixed set of secret names are supported for the quick start (Option A). See the `.github/scripts/export-env.sh` script for the full list.
3. **Provider API Keys**: Standardized names for recognized providers (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are automatically available.

If you need to use a secret with a name that doesn't fit these patterns, you must manually edit `.github/workflows/main.yml` to explicitly expose it to the environment.

## Local Setup Configuration

When running locally, configuration is managed entirely through a `config.yaml` file.

1. **Create a configuration file**:

   ```bash
   # For a minimal setup
   cp config.basic.yaml config.yaml

   # For all features
   cp config.advanced.yaml config.yaml
   ```

2. **Edit `config.yaml`**: Open the file and modify the settings to match your requirements.
3. **Use a `.env` file for secrets** (recommended):

   Create a `.env` file in the root of the project to store your API keys and other secrets. The application will automatically load these into the environment.

   ```
   SUMMARIZER_API_KEY=your_summarizer_key
   RATER_API_KEY=your_rater_key
   SMTP_PASSWORD=your_email_password
   ```

   Then, reference them in `config.yaml`:

   ```yaml
   summarize:
     api_key: env:SUMMARIZER_API_KEY
   ```

## Configuration Reference

### Basic Configuration

#### Run

```yaml
run:
  categories: ["cs.AI", "cs.RO"] # ArXiv categories you're interested in.
  send_log: false # Whether to deliver the log file along with summaries.
  log_dir: ./logs # Directory to store log files.
```

#### Fetch

```yaml
fetch:
  days: 8
  max_results: 200
  max_retries: 10
```

#### Summarizer

```yaml
summarize:
  provider: deepseek
  api_key: env:DEEPSEEK_API_KEY
  base_url: https://api.deepseek.com/v1
  model: deepseek-reasoner
  batch: False
  system_prompt: file:./prompts/summ_lm/system.txt
  user_prompt_template: file:./prompts/summ_lm/user.txt
  completion_options:
    temperature: 0.6
  context_length: 131072
```

#### Paper Rating

```yaml
rate:
  strategy: llm # Can be 'llm', 'embedder', or 'hybrid'.
  top_k: 80 # Max papers to pass to LLM rater in 'hybrid' mode.
  max_selected: 10 # Final number of papers to summarize.
  llm:
    provider: modelscope
    api_key: env:MODELSCOPE_API_KEY
    model: Qwen/Qwen2.5-7B-Instruct
    system_prompt: file:./prompts/rate_lm/system.txt
    user_prompt_template: file:./prompts/rate_lm/user.txt
    criteria:
      novelty:
        description: "How original and innovative are the contributions?"
        weight: 0.3
      methodology:
        description: "How rigorous is the experimental design and evaluation?"
        weight: 0.25
      clarity:
        description: "How well-written and understandable is the paper?"
        weight: 0.2
```

#### Render

```yaml
render:
  formats: ["pdf", "md"] # Supported formats: pdf, html, md, azw3.
  output_dir: ./output
  base_filename: "summary"
```

#### Deliver

```yaml
deliver:
  smtp_server: smtp.example.com
  port: 465
  sender: env:SENDER_EMAIL
  recipient: env:RECIPIENT_EMAIL
  password: env:SMTP_PASSWORD
```

### Advanced Configuration

#### VLM Parsing

For enhanced PDF parsing using Vision Language Models:

```yaml
parse:
  vlm:
    enabled: true
    provider: modelscope
    model: Qwen/Qwen2-VL-72B-Instruct
    api_key: env:VLM_API_KEY
    system_prompt: file:./prompts/parse_vlm/system.txt
    user_prompt_template: file:./prompts/parse_vlm/user.txt
```

#### Embedder Configuration

For similarity-based paper filtering:

```yaml
rate:
  strategy: hybrid
  embedder:
    provider: modelscope
    model: BAAI/bge-large-en-v1.5
    api_key: env:EMBEDDER_API_KEY
    query_prompt: file:./prompts/rate_emb/query.txt
```

### Supported LLM Providers

The following table lists the providers recognized by the system. If you use a recognized provider, you often don't need to specify the `base_url` or `model`.

| Provider              | Example Model                                                  | Requirements        |
| --------------------- | -------------------------------------------------------------- | ------------------- |
| **Anthropic**   | claude-3-opus-20240229                                         | ANTHROPIC_API_KEY   |
| **Cohere**      | command-r-plus, command                                        | COHERE_API_KEY      |
| **DashScope**   | qwen-max, qwen-turbo                                           | DASHSCOPE_API_KEY   |
| **DeepSeek**    | deepseek-reasoner, deepseek-chat                               | DEEPSEEK_API_KEY    |
| **Gemini**      | gemini-1.5-pro, gemini-1.5-flash                               | GEMINI_API_KEY      |
| **Groq**        | llama3-70b-8192, mixtral-8x7b-32768                            | GROQ_API_KEY        |
| **MinerU**      | *For PDF parsing, no specific models*                        | MINERU_API_TOKEN    |
| **Minimax**     | abab6.5-chat                                                   | MINIMAX_API_KEY     |
| **Mistral**     | mistral-large-latest                                           | MISTRAL_API_KEY     |
| **ModelScope**  | Qwen/Qwen2-72B-Instruct, Qwen/Qwen2-57B-A14B-Instruct          | MODELSCOPE_API_KEY  |
| **Moonshot**    | moonshot-v1-128k, moonshot-v1-32k                              | MOONSHOT_API_KEY    |
| **Ollama**      | qwen2:7b, llama3:8b, deepseek-coder-v2:16b                     | Local Installation  |
| **OpenAI**      | gpt-4o, gpt-4-turbo, text-embedding-3-large                    | OPENAI_API_KEY      |
| **OpenRouter**  | anthropic/claude-3.5-sonnet, meta-llama/llama-3.1-70b-instruct | OPENROUTER_API_KEY  |
| **SiliconFlow** | deepseek-ai/DeepSeek-V2, Qwen/Qwen2-72B-Instruct               | SILICONFLOW_API_KEY |
| **Together**    | meta-llama/Llama-3-70b-chat-hf, Qwen/Qwen1.5-72B-Chat          | TOGETHER_API_KEY    |
| **VolcEngine**  | Doubao-pro-128k, Doubao-pro-32k                                | VOLCENGINE_API_KEY  |
| **Zhipu**       | glm-4, glm-3-turbo, embedding-2                                | ZHIPU_API_KEY       |
