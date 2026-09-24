"""
Configuration Management for Laya-OCR-Guard.
Supports Global (~/.guard/config.json) and Local (.guard/config.json).
Provides Interactive Wizard for OpenAI-compatible and Anthropic protocols,
Ping verification, and automatic synchronization to Alibaba OCR CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class LLMProtocol(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMConfig(BaseModel):
    protocol: LLMProtocol = Field(default=LLMProtocol.OPENAI, description="API protocol: openai or anthropic")
    base_url: str = Field(default="https://api.openai.com/v1", description="LLM Base URL")
    api_key: str = Field(default="", description="API Authentication Token")
    model: str = Field(default="gpt-4o", description="Target model name")
    timeout: float = Field(default=30.0, description="HTTP Timeout in seconds")

    @property
    def masked_api_key(self) -> str:
        if not self.api_key:
            return "(none)"
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"


class LayaConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable Laya fast-reflex decision engine")
    model_name: str = Field(default="laya", description="Model checkpoint: laya or laya-multilingual")
    device: str = Field(default="cpu", description="Inference device: cpu or cuda")
    timeout_ms: int = Field(default=150, description="Fast-fail timeout in ms")


class OCRConfig(BaseModel):
    auto_sync: bool = Field(default=True, description="Auto synchronize config to Alibaba OCR CLI")
    binary_path: str = Field(default="ocr", description="Command or path for Alibaba OCR CLI")
    review_timeout: int = Field(default=60, description="Timeout for OCR review in seconds")


class GuardConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    laya: LayaConfig = Field(default_factory=LayaConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)


def get_global_config_path() -> Path:
    return Path.home() / ".guard" / "config.json"


def get_local_config_path(start_path: Optional[Path] = None) -> Path:
    base = start_path or Path.cwd()
    return base / ".guard" / "config.json"


def load_config(repo_path: Optional[Path] = None) -> GuardConfig:
    """
    Load configuration with hierarchy:
    1. Local repo config (.guard/config.json) if exists
    2. Global config (~/.guard/config.json) if exists
    3. Default config
    """
    local_path = get_local_config_path(repo_path)
    if local_path.is_file():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GuardConfig.model_validate(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read local config at {local_path}: {e}[/yellow]")

    global_path = get_global_config_path()
    if global_path.is_file():
        try:
            with open(global_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return GuardConfig.model_validate(data)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read global config at {global_path}: {e}[/yellow]")

    return GuardConfig()


def save_config(config: GuardConfig, local: bool = False, repo_path: Optional[Path] = None) -> Path:
    target_path = get_local_config_path(repo_path) if local else get_global_config_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)
    return target_path


def sync_to_alibaba_ocr(llm: LLMConfig) -> Tuple[bool, str]:
    """
    Synchronize Guard LLM settings to Alibaba Open Code Review CLI:
    `ocr config set llm.url ...`
    `ocr config set llm.auth_token ...`
    `ocr config set llm.model ...`
    """
    ocr_bin = shutil.which("ocr")
    if not ocr_bin:
        return False, "CLI 'ocr' (@alibaba-group/open-code-review) not found in PATH."

    try:
        # Base url
        subprocess.run([ocr_bin, "config", "set", "llm.url", llm.base_url], check=True, capture_output=True, text=True)
        # Auth token (use a placeholder if blank)
        subprocess.run([ocr_bin, "config", "set", "llm.auth_token", llm.api_key or "none"], check=True, capture_output=True, text=True)
        # Model
        subprocess.run([ocr_bin, "config", "set", "llm.model", llm.model], check=True, capture_output=True, text=True)
        return True, "Successfully synced configuration to Alibaba OCR CLI."
    except subprocess.CalledProcessError as e:
        return False, f"Failed to sync to OCR CLI: {e.stderr or e.stdout or str(e)}"
    except Exception as e:
        return False, f"Error executing OCR CLI: {str(e)}"


def run_llm_wizard(local: bool = False, repo_path: Optional[Path] = None) -> GuardConfig:
    """
    Interactive Step-by-Step Wizard for LLM Setup:
    1. Select Protocol: OpenAI-compatible or Anthropic
    2. Input Base URL (with smart defaults & hint for Ollama/DeepSeek)
    3. Input API Key (masked)
    4. Input Model Name (with smart defaults)
    5. Ping Test connection
    6. Save & Auto-sync to Alibaba OCR
    """
    current_cfg = load_config(repo_path)
    console.print(Panel(
        "[bold cyan]🤖 LAYA-OCR-GUARD — LLM CONFIGURATION WIZARD[/bold cyan]\n"
        "[dim]Nhấn Enter để giữ nguyên giá trị mặc định trong ngoặc vuông [ ].[/dim]",
        border_style="cyan"
    ))

    # Step 1: Select Protocol
    console.print("\n[bold yellow]Bước 1: Chọn chuẩn giao thức API (Protocol)[/bold yellow]")
    console.print("  [1] [bold green]OpenAI / OpenAI-Compatible[/bold green] (OpenAI, Ollama, DeepSeek, OpenRouter, vLLM, Groq...)")
    console.print("  [2] [bold magenta]Anthropic[/bold magenta] (Claude API)")
    
    choice = Prompt.ask(
        "Lựa chọn",
        choices=["1", "2"],
        default="1" if current_cfg.llm.protocol == LLMProtocol.OPENAI else "2",
        show_choices=False,
    )

    if choice == "1":
        protocol = LLMProtocol.OPENAI
        default_url = current_cfg.llm.base_url if current_cfg.llm.base_url != "https://api.anthropic.com/v1" else "https://api.openai.com/v1"
        default_model = current_cfg.llm.model if current_cfg.llm.model not in ["claude-3-7-sonnet", "claude-3-5-sonnet"] else "gpt-4o"
    else:
        protocol = LLMProtocol.ANTHROPIC
        default_url = current_cfg.llm.base_url if current_cfg.llm.base_url != "https://api.openai.com/v1" else "https://api.anthropic.com/v1"
        default_model = current_cfg.llm.model if current_cfg.llm.model not in ["gpt-4o", "gpt-4o-mini"] else "claude-3-7-sonnet"

    # Step 2: Base URL
    console.print(f"\n[bold yellow]Bước 2: Base URL[/bold yellow]")
    if protocol == LLMProtocol.OPENAI:
        console.print("[dim]• OpenAI: https://api.openai.com/v1\n• Ollama: http://localhost:11434/v1\n• DeepSeek: https://api.deepseek.com/v1\n• OpenRouter: https://openrouter.ai/api/v1[/dim]")
    else:
        console.print("[dim]• Anthropic: https://api.anthropic.com/v1[/dim]")
        
    base_url = Prompt.ask("Nhập Base URL", default=default_url)

    # Step 3: API Key
    console.print(f"\n[bold yellow]Bước 3: API Key[/bold yellow]")
    env_key = os.environ.get("OPENAI_API_KEY" if protocol == LLMProtocol.OPENAI else "ANTHROPIC_API_KEY", "")
    key_default = current_cfg.llm.api_key or env_key
    
    if protocol == LLMProtocol.OPENAI and ("localhost" in base_url or "127.0.0.1" in base_url):
        console.print("[dim]Dùng local model (Ollama), có thể bấm Enter để trống key.[/dim]")
        api_key = Prompt.ask("API Key (bỏ qua nếu là Ollama)", default=key_default, password=True)
    else:
        api_key = Prompt.ask("Nhập API Key", default=key_default, password=True)

    # Step 4: Model Name
    console.print(f"\n[bold yellow]Bước 4: Model Name[/bold yellow]")
    if protocol == LLMProtocol.OPENAI:
        console.print("[dim]Ví dụ: gpt-4o, gpt-4o-mini, deepseek-chat, qwen2.5-coder:latest[/dim]")
    else:
        console.print("[dim]Ví dụ: claude-3-7-sonnet, claude-3-5-sonnet, claude-3-5-haiku[/dim]")
        
    model = Prompt.ask("Tên Model", default=default_model)

    new_llm = LLMConfig(
        protocol=protocol,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        timeout=current_cfg.llm.timeout,
    )
    current_cfg.llm = new_llm

    # Step 5: Test Ping
    console.print(f"\n[bold yellow]Bước 5: Kiểm tra kết nối (Ping Test)[/bold yellow]")
    do_ping = Confirm.ask("Bạn có muốn gửi ping kiểm tra kết nối ngay không?", default=True)
    if do_ping:
        with console.status("[cyan]Đang gửi request kiểm tra tới LLM...[/cyan]"):
            from guard.core.llm_client import ping_llm
            success, msg, latency = ping_llm(new_llm)
        if success:
            console.print(f"[bold green]✅ Kết nối thành công![/bold green] (Latency: {latency:.0f}ms)")
        else:
            console.print(f"[bold red]❌ Kết nối thất bại:[/bold red] {msg}")
            if not Confirm.ask("Vẫn tiếp tục lưu cấu hình này?", default=True):
                console.print("[yellow]Đã hủy lưu cấu hình.[/yellow]")
                return current_cfg

    # Step 6: Save & Auto-sync
    target_path = save_config(current_cfg, local=local, repo_path=repo_path)
    scope_str = "Local (Repo)" if local else "Global (Toàn máy)"
    console.print(f"[bold green]💾 Đã lưu cấu hình {scope_str} tại:[/bold green] [dim]{target_path}[/dim]")

    if current_cfg.ocr.auto_sync:
        synced, ocr_msg = sync_to_alibaba_ocr(new_llm)
        if synced:
            console.print(f"[bold cyan]🔗 {ocr_msg}[/bold cyan]")
        else:
            console.print(f"[dim yellow]ℹ️  Alibaba OCR Sync: {ocr_msg}[/dim yellow]")

    return current_cfg


def print_config_table(config: GuardConfig, path_info: str):
    table = Table(title=f"🛡️ Guard Configuration ({path_info})", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="bold")
    table.add_column("Parameter")
    table.add_column("Value", style="green")

    table.add_row("LLM", "Protocol", config.llm.protocol.value)
    table.add_row("LLM", "Base URL", config.llm.base_url)
    table.add_row("LLM", "Model", config.llm.model)
    table.add_row("LLM", "API Key", config.llm.masked_api_key)
    table.add_row("LLM", "Timeout", f"{config.llm.timeout}s")

    table.add_row("Laya", "Enabled", str(config.laya.enabled))
    table.add_row("Laya", "Model", config.laya.model_name)
    table.add_row("Laya", "Device", config.laya.device)

    table.add_row("Alibaba OCR", "Auto-Sync", str(config.ocr.auto_sync))
    table.add_row("Alibaba OCR", "CLI Binary", config.ocr.binary_path)
    
    console.print(table)
