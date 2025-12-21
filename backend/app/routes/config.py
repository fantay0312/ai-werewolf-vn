"""
LLM配置管理API
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import get_llm_config, update_llm_config

router = APIRouter()


class LLMConfigRequest(BaseModel):
    """LLM配置请求模型"""
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class LLMConfigResponse(BaseModel):
    """LLM配置响应模型"""
    api_key_set: bool
    api_base: Optional[str]
    model: str
    max_tokens: int
    temperature: float


@router.get("/llm", response_model=LLMConfigResponse)
async def get_config():
    """获取当前LLM配置（不返回完整API Key）"""
    config = get_llm_config()
    return LLMConfigResponse(
        api_key_set=bool(config.api_key),
        api_base=config.api_base,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )


@router.post("/llm", response_model=LLMConfigResponse)
async def set_config(request: LLMConfigRequest):
    """更新LLM配置"""
    config = update_llm_config(
        api_key=request.api_key,
        api_base=request.api_base,
        model=request.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    return LLMConfigResponse(
        api_key_set=bool(config.api_key),
        api_base=config.api_base,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )


@router.post("/llm/test")
async def test_llm_connection():
    """测试LLM连接"""
    from openai import AsyncOpenAI
    config = get_llm_config()

    if not config.api_key:
        return {"success": False, "message": "API Key未设置"}

    try:
        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base
        )

        response = await client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10
        )

        return {
            "success": True,
            "message": "连接成功",
            "model": config.model,
            "response": response.choices[0].message.content
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }
