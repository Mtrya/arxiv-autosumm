"""
Email delivery functionality for ArXiv summarization pipeline.
Handles file attachments with size limits and error detection.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
import os

@dataclass
class DeliveryResult:
    success: bool
    delivered_files: List[str]
    skipped_files: List[Tuple[str,str]] # (file_path, reason)
    error_message: Optional[str]=None

@dataclass
class DelivererConfig:
    smtp_server: str
    port: int
    sender: str
    recipient: str
    password: str
    max_attachment_size_mb: int=25
