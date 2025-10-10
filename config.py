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
    "model": _get_env_str("LLM_MODEL", "qwen-max"),
    "base_url": _get_env_str("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "api_key": _get_env_str("LLM_API_KEY", ""),
    "temperature": _get_env_float("LLM_TEMPERATURE", 0.3),
    "max_tokens": _get_env_int("LLM_MAX_TOKENS", 8000),  # qwen-max最大支持8192
}

# 步骤8专用的大模型配置（用于生成最终分析报告）
LLM_ANALYSIS_CONFIG = {
    "model": _get_env_str("LLM_ANALYSIS_MODEL", "qwen3-max"),
    "base_url": _get_env_str("LLM_ANALYSIS_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "api_key": _get_env_str("LLM_ANALYSIS_API_KEY", ""),  # 如果为空则使用LLM_CONFIG的api_key
    "temperature": _get_env_float("LLM_ANALYSIS_TEMPERATURE", 0.3),
    "max_tokens": _get_env_int("LLM_ANALYSIS_MAX_TOKENS", 10000),  # qwen3-max用于深度分析
}

# LLM模型配置说明:
# 可以通过环境变量或直接修改此处来更改模型
# 支持的模型示例:
# - qwen-max (通义千问)
# - gpt-4 (OpenAI)
# - claude-3-opus (Anthropic)
# 修改方法:
# 1. 修改上面的 LLM_CONFIG 字典中的 "model", "base_url", "api_key"
# 2. 或者设置环境变量 LLM_MODEL, LLM_BASE_URL, LLM_API_KEY

# 报告配置
REPORT_CONFIG = {
    "output_dir": "reports",
    "include_tables": True,
    "include_analysis": True,
}