"""
Connectivity and configuration validation for ArXiv AutoSumm.
Tests API endpoints, authentication, model availability and external dependencies
"""

import os
import smtplib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import requests
import json

from config import MainConfig
from pipeline import (
    BaseClient, BatchConfig, ParserVLMConfig, parse_fast, ParserConfig,
    EmbedderClient
)