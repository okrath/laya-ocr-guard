"""
Unified LLM HTTP Client for Laya-OCR-Guard.
Supports OpenAI-compatible (/v1/chat/completions) and Anthropic (/v1/messages).
Provides lightweight, token-free, sub-second ping verification via /models.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from guard.core.config import LLMConfig, LLMProtocol


class LLMClientError(Exception):
    pass


def ping_llm(cfg: LLMConfig) -> Tuple[bool, str, float]:
    """
    Send a lightweight ping to verify endpoint reachability and credentials.
    Priority 1: GET /models (Standard OpenAI/Ollama/DeepSeek/Gateway ping, 0 tokens, sub-second, no browser lock)
    Priority 2: Fallback to lightweight message if /models is unsupported
    """
    start = time.perf_counter()
    headers = {"Content-Type": "application/json"}
    
    try:
        if cfg.protocol == LLMProtocol.OPENAI:
            # 1. Try standard /models endpoint first (Fast, 0 token, avoids triggering browser turns or heavy generation)
            models_url = f"{cfg.base_url.rstrip('/')}/models"
            if cfg.api_key:
                headers["Authorization"] = f"Bearer {cfg.api_key}"

            try:
                with httpx.Client(timeout=10.0) as client:
                    res = client.get(models_url, headers=headers)
                    latency = (time.perf_counter() - start) * 1000
                    if res.status_code == 200:
                        return True, "OK (Verified via /models)", latency
                    elif res.status_code in [401, 403]:
                        return False, f"HTTP {res.status_code}: API key không hợp lệ hoặc không có quyền truy cập", latency
            except httpx.ConnectError:
                latency = (time.perf_counter() - start) * 1000
                return False, f"Không thể kết nối tới {cfg.base_url}. Service đã khởi động chưa?", latency
            except Exception:
                # If /models hits an unexpected error or 404, fallback to /chat/completions
                pass

            # 2. Fallback to /chat/completions
            url = f"{cfg.base_url.rstrip('/')}/chat/completions"
            payload = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            
            with httpx.Client(timeout=cfg.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                latency = (time.perf_counter() - start) * 1000
                
                if res.status_code == 200:
                    return True, "OK", latency
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:200]}", latency
                    
        elif cfg.protocol == LLMProtocol.ANTHROPIC:
            if cfg.api_key:
                headers["x-api-key"] = cfg.api_key
            headers["anthropic-version"] = "2023-06-01"

            # 1. Try standard /models endpoint first
            models_url = f"{cfg.base_url.rstrip('/')}/models"
            try:
                with httpx.Client(timeout=10.0) as client:
                    res = client.get(models_url, headers=headers)
                    latency = (time.perf_counter() - start) * 1000
                    if res.status_code == 200:
                        return True, "OK (Verified via /models)", latency
                    elif res.status_code in [401, 403]:
                        return False, f"HTTP {res.status_code}: API key không hợp lệ hoặc không có quyền", latency
            except httpx.ConnectError:
                latency = (time.perf_counter() - start) * 1000
                return False, f"Không thể kết nối tới {cfg.base_url}. Service đã khởi động chưa?", latency
            except Exception:
                pass

            # 2. Fallback to /messages
            url = f"{cfg.base_url.rstrip('/')}/messages"
            payload = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            
            with httpx.Client(timeout=cfg.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                latency = (time.perf_counter() - start) * 1000
                
                if res.status_code == 200:
                    return True, "OK", latency
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:200]}", latency
                    
        return False, f"Unsupported protocol: {cfg.protocol}", 0.0

    except httpx.ConnectError:
        latency = (time.perf_counter() - start) * 1000
        return False, f"Không thể kết nối tới {cfg.base_url}. Service đã khởi động chưa?", latency
    except httpx.TimeoutException:
        latency = (time.perf_counter() - start) * 1000
        return False, f"Connection timed out after {cfg.timeout}s (Quá thời gian chờ phản hồi)", latency
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return False, str(e), latency


def call_llm(
    cfg: LLMConfig,
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """
    Execute chat completion call using the configured protocol.
    """
    headers = {"Content-Type": "application/json"}
    
    try:
        if cfg.protocol == LLMProtocol.OPENAI:
            url = f"{cfg.base_url.rstrip('/')}/chat/completions"
            if cfg.api_key:
                headers["Authorization"] = f"Bearer {cfg.api_key}"
            
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: Dict[str, Any] = {
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            with httpx.Client(timeout=cfg.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    raise LLMClientError(f"OpenAI API Error {res.status_code}: {res.text}")
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()

        elif cfg.protocol == LLMProtocol.ANTHROPIC:
            url = f"{cfg.base_url.rstrip('/')}/messages"
            if cfg.api_key:
                headers["x-api-key"] = cfg.api_key
            headers["anthropic-version"] = "2023-06-01"

            payload = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_prompt:
                payload["system"] = system_prompt

            with httpx.Client(timeout=cfg.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    raise LLMClientError(f"Anthropic API Error {res.status_code}: {res.text}")
                data = res.json()
                content = data.get("content", [])
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "".join(text_parts).strip()

        raise LLMClientError(f"Unsupported protocol: {cfg.protocol}")

    except httpx.HTTPError as e:
        raise LLMClientError(f"HTTP Network error: {str(e)}")
    except Exception as e:
        if isinstance(e, LLMClientError):
            raise
        raise LLMClientError(f"Unexpected error: {str(e)}")
