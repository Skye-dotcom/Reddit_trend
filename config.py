# 大模型配置
import os


LLM_CONFIG = {
    "model": os.getenv("LLM_MODEL", "qwen3-max"),
    "base_url": os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "temperature": float(os.getenv("LLM_TEMPERATURE", 0.3)),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", 20000)),
}

# 报告配置
REPORT_CONFIG = {
    "output_dir": "reports",
    "include_tables": True,
    "include_analysis": True,
    "generate_pdf": True,
}