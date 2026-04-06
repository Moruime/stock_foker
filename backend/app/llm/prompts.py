"""各 Agent 的 Prompt 模板。每个函数返回 messages 列表供 LLMClient.chat_json 使用。"""

from __future__ import annotations

import json


# ------------------------------------------------------------------
# 消息面情绪分析
# ------------------------------------------------------------------

def sentiment_prompt(
    stock_code: str,
    stock_name: str,
    news_list: list[dict],
) -> list[dict[str, str]]:
    news_text = "\n".join(
        f"- [{n.get('date', '')}] {n.get('title', '')}  来源: {n.get('source', '')}"
        for n in news_list[:20]
    )
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股消息面分析师。根据提供的个股新闻列表，分析消息面整体多空情绪，"
                "区分有效信息和噪音，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的近期消息面情绪：

股票: {stock_name}({stock_code})

近期新闻:
{news_text}

请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "overall_sentiment": <-1.0到1.0的浮点数，负为利空，正为利好>,
  "sentiment_label": "<利好|利空|中性>",
  "key_news": [
    {{
      "title": "<新闻标题>",
      "sentiment": "<利好|利空|中性>",
      "impact_level": "<高|中|低>",
      "summary": "<一句话概括影响>"
    }}
  ],
  "noise_ratio": <0到1的浮点数，噪音新闻占比>,
  "analysis": "<整体消息面分析总结，2-3句话>"
}}""",
        },
    ]


# ------------------------------------------------------------------
# 板块联动分析
# ------------------------------------------------------------------

def sector_prompt(
    stock_code: str,
    stock_name: str,
    sector_data: dict,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股板块分析师。根据个股所属板块的数据，分析板块走势、"
                "个股在板块中的相对强弱、板块轮动趋势，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的板块联动情况：

股票: {stock_name}({stock_code})

板块数据:
{json.dumps(sector_data, ensure_ascii=False, indent=2)}

请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "sector_name": "<所属行业板块名称>",
  "sector_trend": "<强势|弱势|震荡>",
  "relative_strength": <-1.0到1.0，个股在板块中的相对强弱>,
  "sector_rotation_signal": "<流入|流出|稳定>",
  "related_concepts": [
    {{"name": "<概念板块名>", "activity": "<活跃|一般|冷淡>"}}
  ],
  "top_peers": [
    {{"name": "<同行股票名>", "code": "<股票代码>", "change_pct": <涨跌幅>}}
  ],
  "analysis": "<板块联动分析总结，2-3句话>"
}}""",
        },
    ]


# ------------------------------------------------------------------
# 宏观环境感知
# ------------------------------------------------------------------

def macro_prompt(
    macro_data: dict,
    stock_code: str | None = None,
    stock_name: str | None = None,
) -> list[dict[str, str]]:
    stock_info = f"\n关联个股: {stock_name}({stock_code})" if stock_code else ""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股宏观环境分析师。根据大盘指数、资金流向和市场数据，"
                "判断当前市场阶段和风险等级，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析当前 A 股宏观环境：
{stock_info}

宏观数据:
{json.dumps(macro_data, ensure_ascii=False, indent=2)}

请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "market_phase": "<牛市|熊市|震荡市>",
  "market_sentiment": <-1.0到1.0的浮点数>,
  "key_indicators": [
    {{"name": "<指标名>", "value": "<指标值>", "interpretation": "<解读>"}}
  ],
  "risk_level": "<低|中|高>",
  "impact_on_stock": "<对关联个股的影响评估，若无关联个股则为整体市场评估>",
  "analysis": "<宏观环境分析总结，2-3句话>"
}}""",
        },
    ]


# ------------------------------------------------------------------
# 增强版买卖建议
# ------------------------------------------------------------------

def enhanced_advice_prompt(
    stock_code: str,
    stock_name: str,
    technical_advice: dict,
    sentiment_result: dict,
    sector_result: dict,
    macro_result: dict,
    profile: dict,
    position: dict | None,
) -> list[dict[str, str]]:
    position_info = json.dumps(position, ensure_ascii=False) if position else "无持仓"
    return [
        {
            "role": "system",
            "content": (
                "你是一名资深 A 股投资顾问。你需要综合技术面、消息面、板块联动、宏观环境四个维度，"
                "结合用户的个人交易风格和当前持仓，给出个性化的投资建议。\n"
                "要求：\n"
                "1. 必须综合所有维度进行判断，不能只看单一维度\n"
                "2. 推理过程要清晰可解释\n"
                "3. 如果维度间信号矛盾，需要说明权衡逻辑\n"
                "4. 考虑用户的风险偏好和交易风格"
            ),
        },
        {
            "role": "user",
            "content": f"""请综合分析并给出买卖建议：

股票: {stock_name}({stock_code})

一、技术面分析结果:
{json.dumps(technical_advice, ensure_ascii=False, indent=2)}

二、消息面情绪分析:
{json.dumps(sentiment_result, ensure_ascii=False, indent=2)}

三、板块联动分析:
{json.dumps(sector_result, ensure_ascii=False, indent=2)}

四、宏观环境分析:
{json.dumps(macro_result, ensure_ascii=False, indent=2)}

五、用户炒股画像:
{json.dumps(profile, ensure_ascii=False, indent=2)}

六、当前持仓:
{position_info}

请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "signal": "<buy|sell|hold>",
  "confidence": <0到1的置信度>,
  "reasoning": [
    "<推理步骤1：技术面维度判断>",
    "<推理步骤2：消息面维度判断>",
    "<推理步骤3：板块联动维度判断>",
    "<推理步骤4：宏观环境维度判断>",
    "<推理步骤5：结合用户画像的综合权衡>",
    "<推理步骤6：最终结论>"
  ],
  "dimension_scores": {{
    "technical": <-1到1>,
    "sentiment": <-1到1>,
    "sector": <-1到1>,
    "macro": <-1到1>
  }},
  "risk_warnings": ["<风险提示1>", "<风险提示2>"],
  "position_advice": "<建仓|加仓|减仓|清仓|观望|null>",
  "summary": "<一句话总结建议>"
}}""",
        },
    ]
