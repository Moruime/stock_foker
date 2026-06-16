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
    reports: dict | None = None,
    basicinfo: dict | None = None,
    business: dict | None = None,
    shareholders: dict | None = None,
) -> list[dict[str, str]]:
    news_section = ""
    if news_data and (news_data.get("datas") or news_data.get("chunks_info")):
        news_section = f"""
一、近期新闻与公告（同花顺问财）:
{json.dumps(news_data, ensure_ascii=False, indent=2)}
"""
    events_section = ""
    if events_data and (events_data.get("datas") or events_data.get("chunks_info")):
        events_section = f"""
二、业绩预告与重要事件（同花顺问财，含预告类型、预计净利润、变动原因）:
{json.dumps(events_data, ensure_ascii=False, indent=2)}
"""
    hithink_news_section = ""
    if hithink_news and hithink_news.get("data"):
        items = hithink_news["data"][:10]
        hithink_news_section = f"""
三、财经资讯搜索结果（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    announcements_section = ""
    if announcements and announcements.get("data"):
        items = announcements["data"][:10]
        announcements_section = f"""
四、最新公告信息（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    reports_section = ""
    if reports and reports.get("data"):
        items = reports["data"][:5]
        reports_section = f"""
五、最新研究报告（同花顺问财）:
{json.dumps(items, ensure_ascii=False, indent=2)}
"""
    basicinfo_section = ""
    if basicinfo and (basicinfo.get("datas") or basicinfo.get("chunks_info")):
        basicinfo_section = f"""
六、公司基本资料（同花顺问财）:
{json.dumps(basicinfo, ensure_ascii=False, indent=2)}
"""
    business_section = ""
    if business and (business.get("datas") or business.get("chunks_info")):
        business_section = f"""
七、公司经营数据（同花顺问财）:
{json.dumps(business, ensure_ascii=False, indent=2)}
"""
    shareholders_section = ""
    if shareholders and (shareholders.get("datas") or shareholders.get("chunks_info")):
        shareholders_section = f"""
八、股东股本信息（同花顺问财）:
{json.dumps(shareholders, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股消息面分析师。根据提供的个股新闻、重要事件、财经资讯、公司公告、研究报告、"
                "公司基本资料、经营数据和股东信息，全面分析消息面整体多空情绪，"
                "区分有效信息和噪音，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的近期消息面情绪：

股票: {stock_name}({stock_code})
{news_section}{events_section}{hithink_news_section}{announcements_section}{reports_section}{basicinfo_section}{business_section}{shareholders_section}
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
  "analysis": "<整体消息面分析总结，3-5句话，综合新闻、公告、研报、公司基本面和股东变动做出判断>"
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
    industry_finance = sector_data.pop("industry_finance", {})
    concepts_data = sector_data.pop("concepts", {})
    valuation_section = ""
    if industry_valuation and (industry_valuation.get("datas") or industry_valuation.get("chunks_info")):
        valuation_section = f"""
二、行业估值数据（同花顺问财）:
{json.dumps(industry_valuation, ensure_ascii=False, indent=2)}
"""
    market_section = ""
    if market_data and (market_data.get("datas") or market_data.get("chunks_info")):
        market_section = f"""
三、主力资金流向数据（同花顺问财）:
{json.dumps(market_data, ensure_ascii=False, indent=2)}
"""
    finance_section = ""
    if industry_finance and (industry_finance.get("datas") or industry_finance.get("chunks_info")):
        finance_section = f"""
四、行业财务概况（同花顺问财）:
{json.dumps(industry_finance, ensure_ascii=False, indent=2)}
"""
    concepts_section = ""
    if concepts_data and concepts_data.get("datas"):
        concepts_section = f"""
五、个股所属概念板块（同花顺问财，每条含指数简称、涨跌幅、成份股数量）:
{json.dumps(concepts_data, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股板块分析师。根据个股所属行业板块、行业估值指标（PE/PB/ROE等）、"
                "主力资金流向、行业财务概况，以及个股所属概念板块的实时涨跌幅和成份股规模，"
                "全面分析板块走势、个股在板块中的相对强弱、板块轮动趋势，给出结构化的 JSON 分析结果。"
            ),
        },
        {
            "role": "user",
            "content": f"""请分析以下股票的板块联动情况：

股票: {stock_name}({stock_code})

一、行业板块基础数据（行业名称等基本信息）:
{json.dumps(sector_data, ensure_ascii=False, indent=2)}
{valuation_section}{market_section}{finance_section}{concepts_section}
请以如下 JSON 格式输出（不要输出其他内容）:
{{
  "sector_name": "<所属行业板块名称>",
  "sector_trend": "<强势|弱势|震荡>",
  "relative_strength": <-1.0到1.0，个股在板块中的相对强弱>,
  "sector_rotation_signal": "<流入|流出|稳定>",
  "industry_rank": "<行业在全市场的排名位置描述，如 '前10%' 或 '中游偏上'>",
  "related_concepts": [
    {{"name": "<概念板块名（取自第五部分数据）>", "activity": "<活跃|一般|冷淡，根据涨跌幅判断：>2%活跃、0-2%一般、<0冷淡>"}}
  ],
  "top_peers": [
    {{"name": "<同行股票名>", "code": "<股票代码>", "change_pct": <涨跌幅>}}
  ],
  "analysis": "<板块联动分析总结，3-5句话，综合行业板块走势、估值水平、资金流向、行业财务和概念板块活跃度做出判断>"
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
    # north_flow 现为 AKShare 汇总级数据，单独拼接
    north_flow = macro_data.get("north_flow", {})
    other_market = {k: v for k, v in market_data.items() if k != "north_flow"}
    if any(v for v in other_market.values() if isinstance(v, dict) and v.get("datas")):
        market_section += f"""
市场行情数据（含上证指数、涨跌停家数统计）:
{json.dumps(other_market, ensure_ascii=False, indent=2)}
"""
    if north_flow and north_flow.get("datas"):
        market_section += f"""
沪深港通资金流向汇总（北向 = 沪股通+深股通，南向 = 港股通，单位亿元）:
{json.dumps(north_flow, ensure_ascii=False, indent=2)}
"""
    hithink_section = ""
    if hithink_macro:
        # 检测数据源：_source == "akshare" 表示问财不可用时的兜底数据
        macro_source = hithink_macro.pop("_source", "iwencai")
        source_note = ""
        if macro_source == "akshare":
            source_note = (
                "\n注意：本次宏观数据来自 AKShare 兜底源（东方财富/国家统计局），"
                "其中社融指标替换为'新增信贷同比'（新增人民币贷款当月同比增长），"
                "而非社融存量同比，新增信贷是社融的最大分项，趋势方向一致。\n"
            )
        hithink_section = f"""
宏观经济指标（含 CPI/PPI/PMI 独立查询 + LPR/M2/社融）:
{json.dumps(hithink_macro, ensure_ascii=False, indent=2)}
{source_note}"""
    index_section = ""
    if hithink_index and (hithink_index.get("datas") or hithink_index.get("chunks_info")):
        index_section = f"""
主要指数实时行情（上证指数、沪深300、创业板指，含收盘价、涨跌幅、成交额）:
{json.dumps(hithink_index, ensure_ascii=False, indent=2)}
"""
    return [
        {
            "role": "system",
            "content": (
                "你是一名专业的 A 股宏观环境分析师。根据大盘指数、沪深港通资金流向、涨跌停家数、"
                "宏观经济指标（CPI/PPI/PMI 各自独立查询、LPR/M2/社融等），"
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
    time_frame: str = "short",
    fundamental_data: dict | None = None,
    insresearch_data: dict | None = None,
    reports_data: dict | None = None,
    business_data: dict | None = None,
    basicinfo_data: dict | None = None,
    shareholders_data: dict | None = None,
    memory_context: str = "",
) -> list[dict[str, str]]:
    position_info = json.dumps(position, ensure_ascii=False) if position else "无持仓"
    # 将 time_frame 转换为中文描述
    _tf_map = {"short": "短线（1-5天）", "medium": "中线（1-4周）", "long": "长线（1个月以上）"}
    tf_label = _tf_map.get(time_frame, "短线（1-5天）")
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
                f"重要：用户当前设定的投资周期为「{tf_label}」，"
                "你必须以此时间框架为核心角度给出建议，"
                "包括买卖时机、持仓策略、止盈止损等都应符合该周期的操作特点。\n"
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

★ 用户设定的投资周期: {tf_label}（以此为准，忽略画像中推导的时间框架偏好）

六、当前持仓:
{position_info}
{fundamental_section}{insresearch_section}{reports_section}{business_section}{basicinfo_section}{shareholders_section}
{f"十三、用户记忆与偏好（Memory 系统）:" + chr(10) + memory_context + chr(10) if memory_context else ""}请以如下 JSON 格式输出（不要输出其他内容）:
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
