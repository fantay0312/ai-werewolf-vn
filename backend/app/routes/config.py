"""
LLM配置管理API
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.config import get_llm_config, update_llm_config
from app.security import require_admin_access, validate_llm_api_base

router = APIRouter()
logger = logging.getLogger(__name__)


class LLMConfigRequest(BaseModel):
    """LLM配置请求模型"""
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=16384)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)


class LLMConfigResponse(BaseModel):
    """LLM配置响应模型"""
    api_key_set: bool
    api_base: Optional[str]
    model: str
    max_tokens: int
    temperature: float


@router.get("/llm", response_model=LLMConfigResponse, dependencies=[Depends(require_admin_access)])
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


@router.post("/llm", response_model=LLMConfigResponse, dependencies=[Depends(require_admin_access)])
async def set_config(request: LLMConfigRequest):
    """更新LLM配置"""
    try:
        api_base = validate_llm_api_base(request.api_base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config = update_llm_config(
        api_key=request.api_key,
        api_base=api_base,
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


@router.get("/llm/models", dependencies=[Depends(require_admin_access)])
async def list_models():
    """从配置的 API 提供商获取可用模型列表"""
    from openai import AsyncOpenAI
    config = get_llm_config()

    if not config.api_key:
        return {"success": False, "message": "API Key未设置", "models": []}

    try:
        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base
        )

        models_response = await client.models.list()
        models = sorted(
            [{"id": m.id, "owned_by": m.owned_by} for m in models_response.data],
            key=lambda x: x["id"]
        )

        return {
            "success": True,
            "message": f"获取到 {len(models)} 个模型",
            "models": models
        }
    except Exception as e:
        logger.warning("获取模型列表失败: %s", e)
        return {
            "success": False,
            "message": "获取模型列表失败，请检查配置或稍后重试",
            "models": []
        }


@router.post("/llm/test", dependencies=[Depends(require_admin_access)])
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
        logger.warning("测试LLM连接失败: %s", e)
        return {
            "success": False,
            "message": "连接失败，请检查配置或网络状态"
        }
