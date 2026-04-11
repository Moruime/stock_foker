"""各 Agent 的 Prompt 模板。每个函数返回 messages 列表供 LLMClient.chat_json 使用。"""

from __future__ import annotations

import json


# ------------------------------------------------------------------
# 消息面情绪分析
# ------------------------------------------------------------------

def sentiment_prompt(
    stock_code: str,
    stock_name: str,
    news_data: dict,
    events_data: dict | None = None,
    hithink_news: dict | None = None,
    announcements: dict | None = None,
) -> list[dict[str, str]]:
    news_section = ""
    if news_data and (news_data.get("datas") or news_data.get("chunks_info")):
        news_section = f"""
近期新闻与公告（同花顺问财）:
{json.dumps(news_data, ensure_ascii=False, indent=2)}
"""
    events_section = ""
    if events_data and (events_data.get("datas") or events_data.get("chunks_info")):
        events_section = f"""
近期重要事件（同花顺问财）:
{json.dumps(events_data, ensure_ascii=False, indent=2)}
"""
    hithink_news_section = ""
    if hithink_news and hithink_news.get("data"):
        # 截取前 10 条财经资讯避免 Prompt 过长
        items = hithink_news["data"][:10]
        hithink_news_section = f"""
财经资讯搜索结果（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    announcements_section = ""
    if announcements and announcements.get("data"):
        items = announcements["data"][:10]
        announcements_section = f"""
最新公告信息（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股消息面分析师。根据提供的个股新闻列表、重要事件、财经资讯和公司公告，分析消息面整体多空情绪，"
                "区分有效信息和噪音，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的近期消息面情绪：

股票: {stock_name}({stock_code})
{news_section}{events_section}{hithink_news_section}{announcements_section}
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
    industry_valuation = sector_data.pop("industry_valuation", {})
    market_data = sector_data.pop("market_data", {})
    valuation_section = ""
    if industry_valuation and (industry_valuation.get("datas") or industry_valuation.get("chunks_info")):
        valuation_section = f"""

行业估值数据（同花顺问财）:
{json.dumps(industry_valuation, ensure_ascii=False, indent=2)}
"""
    market_section = ""
    if market_data and (market_data.get("datas") or market_data.get("chunks_info")):
        market_section = f"""

主力资金流向数据（同花顺问财）:
{json.dumps(market_data, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股板块分析师。根据个股所属板块的数据、行业估值指标（PE/PB/ROE等）和主力资金流向，分析板块走势、"
                "个股在板块中的相对强弱、板块轮动趋势，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的板块联动情况：

股票: {stock_name}({stock_code})

板块数据:
{json.dumps(sector_data, ensure_ascii=False, indent=2)}
{valuation_section}{market_section}
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
    # 所有数据均来自同花顺问财 API
    hithink_macro = macro_data.get("hithink_macro", {})
    hithink_index = macro_data.get("hithink_index", {})
    market_data = {k: v for k, v in macro_data.items() if k not in ("hithink_macro", "hithink_index")}
    market_section = ""
    if any(v for v in market_data.values() if isinstance(v, dict) and v.get("datas")):
        market_section = f"""
市场行情数据（同花顺问财）:
{json.dumps(market_data, ensure_ascii=False, indent=2)}
"""
    hithink_section = ""
    if hithink_macro:
        hithink_section = f"""
宏观经济指标（同花顺问财）:
{json.dumps(hithink_macro, ensure_ascii=False, indent=2)}
"""
    index_section = ""
    if hithink_index and (hithink_index.get("datas") or hithink_index.get("chunks_info")):
        index_section = f"""
主要指数实时行情（同花顺问财）:
{json.dumps(hithink_index, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股宏观环境分析师。根据大盘指数、资金流向和宏观经济指标（CPI/PPI/PMI/LPR/M2等），"
                "判断当前市场阶段和风险等级，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析当前 A 股宏观环境：
{stock_info}
{market_section}{hithink_section}{index_section}
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
    fundamental_data: dict | None = None,
    insresearch_data: dict | None = None,
    reports_data: dict | None = None,
    business_data: dict | None = None,
    basicinfo_data: dict | None = None,
    shareholders_data: dict | None = None,
) -> list[dict[str, str]]:
    position_info = json.dumps(position, ensure_ascii=False) if position else "无持仓"
    fundamental_section = ""
    if fundamental_data and (fundamental_data.get("datas") or fundamental_data.get("chunks_info")):
        fundamental_section = f"""
七、基本面财务数据（同花顺问财）:
{json.dumps(fundamental_data, ensure_ascii=False, indent=2)}
"""
    insresearch_section = ""
    if insresearch_data and (insresearch_data.get("datas") or insresearch_data.get("chunks_info")):
        insresearch_section = f"""
八、机构评级与研究（同花顺问财）:
{json.dumps(insresearch_data, ensure_ascii=False, indent=2)}
"""
    reports_section = ""
    if reports_data and reports_data.get("data"):
        # 截取前 5 条研报避免 Prompt 过长
        items = reports_data["data"][:5]
        reports_section = f"""
九、最新研究报告（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    business_section = ""
    if business_data and (business_data.get("datas") or business_data.get("chunks_info")):
        business_section = f"""
十、公司经营数据（同花顺问财）:
{json.dumps(business_data, ensure_ascii=False, indent=2)}
"""
    basicinfo_section = ""
    if basicinfo_data and (basicinfo_data.get("datas") or basicinfo_data.get("chunks_info")):
        basicinfo_section = f"""
十一、公司基本资料（同花顺问财）:
{json.dumps(basicinfo_data, ensure_ascii=False, indent=2)}
"""
    shareholders_section = ""
    if shareholders_data and (shareholders_data.get("datas") or shareholders_data.get("chunks_info")):
        shareholders_section = f"""
十二、股东股本信息（同花顺问财）:
{json.dumps(shareholders_data, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名资深 A 股投资顾问。你需要综合技术面、消息面、板块联动、宏观环境、基本面五个维度，"
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
{fundamental_section}{insresearch_section}{reports_section}{business_section}{basicinfo_section}{shareholders_section}
请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "signal": "<buy|sell|hold>",
  "confidence": <0到1的置信度>,
  "reasoning": [
    "<推理步骤1：技术面维度判断>",
    "<推理步骤2：消息面维度判断>",
    "<推理步骤3：板块联动维度判断>",
    "<推理步骤4：宏观环境维度判断>",
    "<推理步骤5：基本面/机构评级维度判断>",
    "<推理步骤6：结合用户画像的综合权衡>",
    "<推理步骤7：最终结论>"
  ],
  "dimension_scores": {{
    "technical": <-1到1>,
    "sentiment": <-1到1>,
    "sector": <-1到1>,
    "macro": <-1到1>,
    "fundamental": <-1到1>
  }},
  "risk_warnings": ["<风险提示1>", "<风险提示2>"],
  "position_advice": "<建仓|加仓|减仓|清仓|观望|null>",
  "summary": "<一句话总结建议>"
}}""",
        },
    ]
