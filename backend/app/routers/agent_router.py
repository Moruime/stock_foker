"""Agent API 路由 — 消息面 / 板块 / 宏观 / 综合分析 / LLM 状态。"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db, SessionLocal
from app.models.models import AgentResultCache, DailyAgentSnapshot, FocusStock, DataSourceCache
from app.models.schemas import (
    AgentResultResponse,
    AgentRunRequest,
    EnhancedAnalysisResponse,
    LLMStatusResponse,
)
from app.agents.sentiment_agent import SentimentAgent
from app.agents.sector_agent import SectorAgent
from app.agents.macro_agent import MacroAgent
from app.agents.enhanced_advice_agent import EnhancedAdviceAgent
from app.llm.client import get_llm_client, reload_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _cache_key_today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _last_9am() -> datetime:
    """返回最近一次 09:00 的时间点，作为每日缓存新鲜度边界。"""
    now = datetime.now()
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return today_9am if now >= today_9am else today_9am - timedelta(days=1)


def _get_cached(db: Session, agent_name: str, stock_code: str) -> dict | None:
    """查询新鲜缓存：在上一个 09:00 之后生成才算新鲜。LLM 可用时降级结果跳过。"""
    row = db.query(AgentResultCache).filter(
        AgentResultCache.agent_name == agent_name,
        AgentResultCache.stock_code == stock_code,
        AgentResultCache.created_at >= _last_9am(),
    ).order_by(AgentResultCache.created_at.desc()).first()
    if row:
        # LLM 现在可用但缓存是未使用 LLM 的降级结果 → 跳过缓存重新分析
        if not row.llm_used and get_llm_client().is_available():
            return None
        return {
            "agent_name": row.agent_name,
            "status": row.status,
            "data": json.loads(row.data),
            "llm_used": bool(row.llm_used),
            "timestamp": row.created_at.isoformat() if row.created_at else "",
            "error_message": row.error_message,
        }
    return None


def _get_stale_cached(db: Session, agent_name: str, stock_code: str) -> dict | None:
    """查询最近一条缓存（含过期），用于页面刷新时恢复显示旧数据。"""
    row = db.query(AgentResultCache).filter(
        AgentResultCache.agent_name == agent_name,
        AgentResultCache.stock_code == stock_code,
    ).order_by(AgentResultCache.created_at.desc()).first()
    if row:
        return {
            "agent_name": row.agent_name,
            "status": row.status,
            "data": json.loads(row.data),
            "llm_used": bool(row.llm_used),
            "timestamp": row.created_at.isoformat() if row.created_at else "",
            "error_message": row.error_message,
        }
    return None


def _save_cache(db: Session, result: dict, stock_code: str) -> None:
    """写入或更新缓存。created_at 使用本地时间（避免 SQLite CURRENT_TIMESTAMP 的 UTC 问题）。"""
    agent_name = result["agent_name"]
    cache_key = _cache_key_today()
    now = datetime.now()
    existing = db.query(AgentResultCache).filter(
        AgentResultCache.agent_name == agent_name,
        AgentResultCache.stock_code == stock_code,
        AgentResultCache.cache_key == cache_key,
    ).first()
    if existing:
        existing.status = result["status"]
        existing.llm_used = int(result["llm_used"])
        existing.data = json.dumps(result["data"], ensure_ascii=False)
        existing.error_message = result.get("error_message")
        existing.created_at = now
    else:
        row = AgentResultCache(
            agent_name=agent_name,
            stock_code=stock_code,
            cache_key=cache_key,
            status=result["status"],
            llm_used=int(result["llm_used"]),
            data=json.dumps(result["data"], ensure_ascii=False),
            error_message=result.get("error_message"),
            created_at=now,
        )
        db.add(row)
    db.commit()


def _run_agent(agent, **kwargs) -> dict:
    """执行单个 Agent 并返回 dict。"""
    return agent.execute(**kwargs).to_dict()


def _run_agent_in_thread(agent, **kwargs) -> dict:
    """在独立线程中执行 Agent（创建独立 DB Session 避免跨线程共享）。"""
    thread_db = SessionLocal()
    try:
        kwargs["db"] = thread_db
        return agent.execute(**kwargs).to_dict()
    finally:
        thread_db.close()


# ------------------------------------------------------------------
# 快照工具函数
# ------------------------------------------------------------------

# 每种 Agent 需要保存到快照的关键字段
_SNAPSHOT_FIELDS: dict[str, list[str]] = {
    "sentiment": ["overall_sentiment", "sentiment_label", "raw_news_count", "noise_ratio", "analysis"],
    "sector":    ["sector_name", "sector_trend", "relative_strength", "sector_rotation_signal", "industry_rank", "analysis"],
    "macro":     ["market_phase", "market_sentiment", "risk_level", "impact_on_stock", "analysis"],
    "enhanced_advice": ["signal", "confidence", "summary", "position_advice", "reasoning", "risk_warnings", "dimension_scores"],
}


def _save_snapshot(db: Session, result: dict, stock_code: str) -> None:
    """Agent 运行成功后，抽取关键指标写入每日快照表。每种 Agent 每支股票每天仅保留最新一条。"""
    agent_name = result.get("agent_name", "")
    if agent_name not in _SNAPSHOT_FIELDS:
        return
    if result.get("status") == "error":
        return
    today = datetime.now().strftime("%Y-%m-%d")
    data = result.get("data", {})
    snapshot = {k: data.get(k) for k in _SNAPSHOT_FIELDS[agent_name]}

    existing = db.query(DailyAgentSnapshot).filter(
        DailyAgentSnapshot.agent_type == agent_name,
        DailyAgentSnapshot.stock_code == stock_code,
        DailyAgentSnapshot.date == today,
    ).first()

    if existing:
        existing.snapshot_data = json.dumps(snapshot, ensure_ascii=False)
        existing.llm_used = int(result.get("llm_used", False))
    else:
        row = DailyAgentSnapshot(
            agent_type=agent_name,
            stock_code=stock_code,
            date=today,
            snapshot_data=json.dumps(snapshot, ensure_ascii=False),
            llm_used=int(result.get("llm_used", False)),
        )
        db.add(row)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("快照写入失败 agent=%s stock=%s: %s", agent_name, stock_code, exc)


# ------------------------------------------------------------------
# 单 Agent 端点
# ------------------------------------------------------------------

@router.post("/sentiment", response_model=AgentResultResponse)
def run_sentiment(req: AgentRunRequest, db: Session = Depends(get_db)):
    """消息面情绪分析。"""
    cached = _get_cached(db, "sentiment", req.stock_code)
    if cached:
        return cached
    result = _run_agent(
        SentimentAgent(),
        stock_code=req.stock_code,
        stock_name=req.stock_name,
        db=db,
    )
    _save_cache(db, result, req.stock_code)
    _save_snapshot(db, result, req.stock_code)
    return result


@router.post("/sector", response_model=AgentResultResponse)
def run_sector(req: AgentRunRequest, db: Session = Depends(get_db)):
    """板块联动分析。"""
    cached = _get_cached(db, "sector", req.stock_code)
    if cached:
        return cached
    result = _run_agent(
        SectorAgent(),
        stock_code=req.stock_code,
        stock_name=req.stock_name,
        db=db,
    )
    _save_cache(db, result, req.stock_code)
    _save_snapshot(db, result, req.stock_code)
    return result


@router.post("/macro", response_model=AgentResultResponse)
def run_macro(req: AgentRunRequest, db: Session = Depends(get_db)):
    """宏观环境分析。"""
    cached = _get_cached(db, "macro", req.stock_code)
    if cached:
        return cached
    result = _run_agent(MacroAgent(), stock_code=req.stock_code, stock_name=req.stock_name, db=db)
    _save_cache(db, result, req.stock_code)
    _save_snapshot(db, result, req.stock_code)
    return result


# ------------------------------------------------------------------
# 综合分析（链路端点）
# ------------------------------------------------------------------

@router.get("/enhanced-analysis/cached/{stock_code}", response_model=EnhancedAnalysisResponse)
def get_enhanced_analysis_cached(stock_code: str, db: Session = Depends(get_db)):
    """仅返回 DB 缓存中的综合分析结果（含过期数据），不运行任何 Agent。没有缓存则 404。"""
    cached_enhanced = _get_stale_cached(db, "enhanced_advice", stock_code)
    if not cached_enhanced:
        raise HTTPException(status_code=404, detail="未找到当天缓存")
    _empty: dict = {
        "agent_name": "",
        "status": "success",
        "data": {},
        "llm_used": False,
        "timestamp": datetime.now().isoformat(),
        "error_message": None,
    }
    return {
        "sentiment": _get_cached(db, "sentiment", stock_code) or {**_empty, "agent_name": "sentiment"},
        "sector": _get_cached(db, "sector", stock_code) or {**_empty, "agent_name": "sector"},
        "macro": _get_cached(db, "macro", stock_code) or {**_empty, "agent_name": "macro"},
        "enhanced_advice": cached_enhanced,
    }


@router.post("/enhanced-analysis", response_model=EnhancedAnalysisResponse)
def run_enhanced_analysis(req: AgentRunRequest, db: Session = Depends(get_db)):
    """综合 AI 分析 — 并行运行 3 个上游 Agent，再运行增强建议 Agent。"""
    stock_code = req.stock_code
    stock_name = req.stock_name

    # 0. 先检查 enhanced_advice 整体缓存，命中则直接拼装响应返回
    cached_enhanced = _get_cached(db, "enhanced_advice", stock_code)
    if cached_enhanced:
        _empty: dict = {
            "agent_name": "",
            "status": "success",
            "data": {},
            "llm_used": False,
            "timestamp": datetime.now().isoformat(),
            "error_message": None,
        }
        return {
            "sentiment": _get_cached(db, "sentiment", stock_code) or {**_empty, "agent_name": "sentiment"},
            "sector": _get_cached(db, "sector", stock_code) or {**_empty, "agent_name": "sector"},
            "macro": _get_cached(db, "macro", stock_code) or {**_empty, "agent_name": "macro"},
            "enhanced_advice": cached_enhanced,
        }

    # 1. 并行执行上游 3 个 Agent（优先用缓存）
    upstream_results: dict[str, dict] = {}
    agents_to_run: dict[str, tuple] = {}

    for name, cls in [("sentiment", SentimentAgent), ("sector", SectorAgent), ("macro", MacroAgent)]:
        cached = _get_cached(db, name, stock_code)
        if cached:
            upstream_results[name] = cached
        else:
            agents_to_run[name] = (cls(),)

    if agents_to_run:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    _run_agent_in_thread,
                    agent_tuple[0],
                    stock_code=stock_code,
                    stock_name=stock_name,
                ): name
                for name, agent_tuple in agents_to_run.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    upstream_results[name] = result
                    # 使用主线程 db 写缓存和快照
                    _save_cache(db, result, stock_code)
                    _save_snapshot(db, result, stock_code)
                except Exception as e:
                    logger.error("Agent %s 执行异常: %s", name, e)
                    upstream_results[name] = {
                        "agent_name": name,
                        "status": "error",
                        "data": {},
                        "llm_used": False,
                        "timestamp": datetime.now().isoformat(),
                        "error_message": str(e),
                    }

    # 2. 获取 K 线数据和技术指标（用于增强建议）
    from app.services.stock_service import get_kline_data, calculate_indicators

    try:
        kline = get_kline_data(stock_code, "daily", db=db)
        indicators = calculate_indicators(kline)
    except Exception as e:
        logger.warning("获取K线/指标失败: %s", e)
        kline = []
        indicators = {}

    # 3. 运行增强建议 Agent
    enhanced_result = _run_agent(
        EnhancedAdviceAgent(),
        stock_code=stock_code,
        stock_name=stock_name,
        kline=kline,
        indicators=indicators,
        db=db,
        sentiment_result=upstream_results.get("sentiment", {}).get("data", {}),
        sector_result=upstream_results.get("sector", {}).get("data", {}),
        macro_result=upstream_results.get("macro", {}).get("data", {}),
    )
    _save_cache(db, enhanced_result, stock_code)
    _save_snapshot(db, enhanced_result, stock_code)

    return {
        "sentiment": upstream_results.get("sentiment", {"agent_name": "sentiment", "status": "error", "data": {}, "llm_used": False, "timestamp": datetime.now().isoformat(), "error_message": "未执行"}),
        "sector": upstream_results.get("sector", {"agent_name": "sector", "status": "error", "data": {}, "llm_used": False, "timestamp": datetime.now().isoformat(), "error_message": "未执行"}),
        "macro": upstream_results.get("macro", {"agent_name": "macro", "status": "error", "data": {}, "llm_used": False, "timestamp": datetime.now().isoformat(), "error_message": "未执行"}),
        "enhanced_advice": enhanced_result,
    }


# ------------------------------------------------------------------
# LLM 状态
# ------------------------------------------------------------------

@router.get("/llm-status", response_model=LLMStatusResponse)
def get_llm_status():
    """获取 LLM 配置状态（脱敏）。"""
    return get_llm_client().get_status()


@router.post("/reload-config", response_model=LLMStatusResponse)
def reload_config():
    """重新加载 .env 中的 LLM 配置（无需重启后端）。"""
    from dotenv import load_dotenv
    import os

    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(os.path.abspath(env_path), override=True)

    client = reload_llm_client()
    return client.get_status()


# ------------------------------------------------------------------
# 清除缓存
# ------------------------------------------------------------------

@router.delete("/cache/{stock_code}")
def clear_agent_cache(stock_code: str, db: Session = Depends(get_db)):
    """清除指定股票的 Agent 缓存和数据源缓存。"""
    count = db.query(AgentResultCache).filter(
        AgentResultCache.stock_code == stock_code,
    ).delete()
    ds_count = db.query(DataSourceCache).filter(
        DataSourceCache.stock_code == stock_code,
    ).delete()
    db.commit()
    return {"message": f"已清除 {count} 条 Agent 缓存, {ds_count} 条数据源缓存"}
