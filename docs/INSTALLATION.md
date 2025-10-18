# Installation Guide

This guide provides detailed instructions for installing and deploying ArXiv AutoSumm. Choose the method that best fits your needs.

## Advanced Installation

This guide covers advanced installation methods for users who need more control and customization than the [Quick Start](https://github.com/your-username/arxiv-autosumm#quick-start-github-actions) provides.

### GitHub Actions with `config.yaml`

For full control over the pipeline, you can use a `config.yaml` file in your repository instead of relying on secrets for dynamic configuration.

1. **Set Repository Variable**: In your forked repository, go to **Settings** > **Variables** > **Actions** and add a new **variable** `USE_REPO_CONFIG` with the value `true`.
2. **Create `config.yaml`**: Copy the `config.advanced.yaml` to `config.yaml` and customize it. You can define all pipeline settings here, including prompts, models, and rating criteria.
3. **Use Secrets for Keys**: For security, continue to use repository secrets for API keys and passwords, referencing them in your `config.yaml` with the `env:SECRET_NAME` syntax.

For a complete reference of all configuration options, see the [Configuration Guide](CONFIGURATION.md).

## Method 2: Local Setup with Git Clone

Full local control over execution timing and configuration.

#### Prerequisites

**System Requirements:**

- Git
- Python 3.11+
- System dependencies (based on desired output formats)

**Optional System Dependencies:**

```bash
# For PDF output
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex

# For HTML output
sudo apt-get install pandoc

# For AZW3 (Kindle) output
sudo apt-get install calibre

# Install all at once
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-xetex pandoc calibre
```

#### Installation Steps

1. **Clone Repository**

   ```bash
   git clone https://github.com/your-username/arxiv-autosumm.git
   cd arxiv-autosumm
   ```

2. **Install Python Dependencies**

   ```bash
   pip install -e .
   ```

3. **Configure Application**

   **Basic Configuration:**

   ```bash
   cp config.basic.yaml config.yaml
   # Edit config.yaml with your settings
   ```

   **Advanced Configuration:**

   ```bash
   cp config.advanced.yaml config.yaml
   # Edit config.yaml for advanced features
   ```

   **Environment Variables** (alternative to config file):

   ```bash
   # Create .env file
   echo "SUMMARIZER_API_KEY=your_key" > .env
   echo "RATER_API_KEY=your_key" >> .env
   echo "SMTP_PASSWORD=your_password" >> .env
   ```

4. **Test Configuration**

   ```bash
   autosumm run --test
   ```

5. **Run Pipeline**

   ```bash
   # Normal execution
   autosumm run

   # Verbose output
   autosumm run --verbose

   # Single category only
   autosumm run --specify-category cs.AI
   ```

#### Local Scheduling

For automated execution, you can use either systemd (recommended) or crontab.

##### Systemd Timer (Recommended)

Create a systemd service and timer for modern, reliable scheduling:

```bash
# Create systemd service file
sudo tee ~/.config/systemd/user/arxiv-autosumm.service > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm Service
After=network.target

[Service]
Type=oneshot
User=your-username
WorkingDirectory=/path/to/arxiv-autosumm # replace with real directory
ExecStart=/usr/bin/python -m autosumm.cli run # replace with your python path
StandardOutput=journal
StandardError=journal
EOF

# Create systemd timer file
sudo tee ~/.config/systemd/user/arxiv-autosumm.timer > /dev/null << 'EOF'
[Unit]
Description=ArXiv AutoSumm Timer
Requires=arxiv-autosumm.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Reload systemd and enable timer
sudo systemctl daemon-reload
sudo systemctl enable arxiv-autosumm.timer
sudo systemctl start arxiv-autosumm.timer

# Check timer status
systemctl list-timers --all
```

##### Crontab (Alternative)

For systems without systemd, use traditional crontab:

```bash
# Edit crontab
crontab -e

# Run daily at 9 AM
0 9 * * * cd /path/to/arxiv-autosumm && autosumm run

# Run every 6 hours
0 */6 * * * cd /path/to/arxiv-autosumm && autosumm run
```
