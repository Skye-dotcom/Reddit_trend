# 大模型配置
import os


def _get_env_str(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value and value.strip() else default


def _get_env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if not value or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if not value or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


LLM_CONFIG = {
    "model": _get_env_str("LLM_MODEL", "qwen3-max"),
    "base_url": _get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "api_key": _get_env_str("LLM_API_KEY", ""),
    "temperature": _get_env_float("LLM_TEMPERATURE", 0.3),
    "max_tokens": _get_env_int("LLM_MAX_TOKENS", 20000),
}

# 报告配置
REPORT_CONFIG = {
    "output_dir": "reports",
    "include_tables": True,
    "include_analysis": True,
    "generate_pdf": True,
}