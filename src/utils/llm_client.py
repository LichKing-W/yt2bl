"""共享的 OpenAI 兼容 LLM 客户端。

将字幕翻译、B 站标题/标签生成中重复的 chat completion 调用集中到一处，
统一管理端点配置（base_url/api_key）、错误处理与调试日志。
"""

from typing import Optional

from .logger import logger


async def llm_complete(
    system_prompt: str,
    user_input: str,
    api_key: str,
    *,
    model: str = "gpt-4o-mini",
    base_url: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    debug_label: str = "LLM",
) -> str:
    """调用 OpenAI 兼容的 chat completion 接口。

    Args:
        system_prompt: system 角色内容（通常是 prompt 模板）。
        user_input: user 角色内容。
        api_key: API 密钥。
        model: 模型名。
        base_url: 可选的自定义 API 端点。
        temperature: 采样温度。
        max_tokens: 最大输出 token 数。
        debug_label: 调试日志中的标记名（会拼成 ``[{label}原始输出]``）。

    Returns:
        第一条回复的文本内容（已 strip）。
    """
    try:
        import openai
    except ImportError:
        logger.error("未安装openai库，请运行: pip install openai")
        raise

    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
        logger.info(f"使用自定义API端点: {base_url}")

    client = openai.AsyncOpenAI(**client_kwargs)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = response.choices[0].message.content.strip()
        logger.debug(f"[{debug_label}原始输出]\n{result}\n[/{debug_label}原始输出]")
        return result
    except Exception as e:
        logger.error(f"LLM API调用失败: {str(e)}")
        raise
