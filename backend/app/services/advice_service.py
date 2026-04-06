"""基于技术指标的简单买卖建议服务"""


def generate_advice(indicators: dict, kline_data: list[dict]) -> dict:
    """根据技术指标生成买卖建议

    综合 MACD、KDJ、RSI、均线等指标，给出带推理过程的建议。
    """
    if not kline_data or len(kline_data) < 20:
        return {
            "signal": "hold",
            "confidence": 0,
            "reasoning": ["数据不足，无法生成有效建议"],
            "indicators_summary": {},
        }

    signals = []
    reasoning = []
    summary = {}

    current_price = kline_data[-1]["close"]
    summary["current_price"] = current_price

    # --- MACD 分析 ---
    macd = indicators.get("macd", {})
    if macd and macd.get("dif") and macd.get("dea"):
        dif = _last_valid(macd["dif"])
        dea = _last_valid(macd["dea"])
        hist = _last_valid(macd.get("histogram", []))
        prev_hist = _prev_valid(macd.get("histogram", []))

        if dif is not None and dea is not None:
            summary["macd_dif"] = round(dif, 4)
            summary["macd_dea"] = round(dea, 4)

            if dif > dea:
                if prev_hist is not None and hist is not None and prev_hist <= 0 < hist:
                    signals.append(1.5)
                    reasoning.append(f"MACD金叉信号：DIF({dif:.4f})上穿DEA({dea:.4f})，偏多")
                else:
                    signals.append(0.5)
                    reasoning.append(f"MACD多头排列：DIF({dif:.4f}) > DEA({dea:.4f})")
            else:
                if prev_hist is not None and hist is not None and prev_hist >= 0 > hist:
                    signals.append(-1.5)
                    reasoning.append(f"MACD死叉信号：DIF({dif:.4f})下穿DEA({dea:.4f})，偏空")
                else:
                    signals.append(-0.5)
                    reasoning.append(f"MACD空头排列：DIF({dif:.4f}) < DEA({dea:.4f})")

    # --- KDJ 分析 ---
    kdj = indicators.get("kdj", {})
    if kdj and kdj.get("k") and kdj.get("d"):
        k = _last_valid(kdj["k"])
        d = _last_valid(kdj["d"])
        j = _last_valid(kdj.get("j", []))

        if k is not None and d is not None:
            summary["kdj_k"] = round(k, 2)
            summary["kdj_d"] = round(d, 2)
            if j is not None:
                summary["kdj_j"] = round(j, 2)

            if k < 20 and d < 20:
                signals.append(1)
                reasoning.append(f"KDJ超卖区：K({k:.1f}), D({d:.1f}) 均低于20，存在反弹机会")
            elif k > 80 and d > 80:
                signals.append(-1)
                reasoning.append(f"KDJ超买区：K({k:.1f}), D({d:.1f}) 均高于80，注意回调风险")
            elif k > d:
                signals.append(0.3)
                reasoning.append(f"KDJ偏多：K({k:.1f}) > D({d:.1f})")
            else:
                signals.append(-0.3)
                reasoning.append(f"KDJ偏空：K({k:.1f}) < D({d:.1f})")

    # --- RSI 分析 ---
    rsi_list = indicators.get("rsi", [])
    rsi = _last_valid(rsi_list)
    if rsi is not None:
        summary["rsi"] = round(rsi, 2)
        if rsi < 30:
            signals.append(1)
            reasoning.append(f"RSI超卖({rsi:.1f})：低于30，股价可能被低估")
        elif rsi > 70:
            signals.append(-1)
            reasoning.append(f"RSI超买({rsi:.1f})：高于70，股价可能被高估")
        else:
            reasoning.append(f"RSI中性区域({rsi:.1f})")

    # --- 均线分析 ---
    ma5 = _last_valid(indicators.get("ma5", []))
    ma10 = _last_valid(indicators.get("ma10", []))
    ma20 = _last_valid(indicators.get("ma20", []))

    if ma5 is not None and ma10 is not None and ma20 is not None:
        summary["ma5"] = round(ma5, 2)
        summary["ma10"] = round(ma10, 2)
        summary["ma20"] = round(ma20, 2)

        if current_price > ma5 > ma10 > ma20:
            signals.append(1)
            reasoning.append(
                f"均线多头排列：价格({current_price:.2f}) > MA5({ma5:.2f}) > "
                f"MA10({ma10:.2f}) > MA20({ma20:.2f})，趋势向上"
            )
        elif current_price < ma5 < ma10 < ma20:
            signals.append(-1)
            reasoning.append(
                f"均线空头排列：价格({current_price:.2f}) < MA5({ma5:.2f}) < "
                f"MA10({ma10:.2f}) < MA20({ma20:.2f})，趋势向下"
            )
        else:
            reasoning.append("均线交织，趋势不明朗")

    # --- 布林带分析 ---
    boll = indicators.get("boll", {})
    if boll and boll.get("upper") and boll.get("lower"):
        upper = _last_valid(boll["upper"])
        lower = _last_valid(boll["lower"])
        middle = _last_valid(boll.get("middle", []))

        if upper is not None and lower is not None:
            summary["boll_upper"] = round(upper, 2)
            summary["boll_lower"] = round(lower, 2)

            if current_price >= upper:
                signals.append(-0.8)
                reasoning.append(
                    f"股价({current_price:.2f})触及布林带上轨({upper:.2f})，"
                    "短期有回调压力"
                )
            elif current_price <= lower:
                signals.append(0.8)
                reasoning.append(
                    f"股价({current_price:.2f})触及布林带下轨({lower:.2f})，"
                    "短期有支撑"
                )

    # --- 综合判断 ---
    if not signals:
        return {
            "signal": "hold",
            "confidence": 0,
            "reasoning": ["技术指标数据不足，建议观望"],
            "indicators_summary": summary,
        }

    avg_signal = sum(signals) / len(signals)
    confidence = min(abs(avg_signal) / 1.5, 1.0)

    if avg_signal > 0.3:
        signal = "buy"
        reasoning.append(
            f"综合评分: {avg_signal:.2f}，多项指标偏多，建议关注买入机会"
        )
    elif avg_signal < -0.3:
        signal = "sell"
        reasoning.append(
            f"综合评分: {avg_signal:.2f}，多项指标偏空，建议考虑减仓或观望"
        )
    else:
        signal = "hold"
        reasoning.append(
            f"综合评分: {avg_signal:.2f}，多空分歧，建议持有观望"
        )

    return {
        "signal": signal,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "indicators_summary": summary,
    }


def _last_valid(lst: list) -> float | None:
    """获取列表中最后一个非 None 值"""
    for v in reversed(lst):
        if v is not None:
            return float(v)
    return None


def _prev_valid(lst: list) -> float | None:
    """获取列表中倒数第二个非 None 值"""
    count = 0
    for v in reversed(lst):
        if v is not None:
            count += 1
            if count == 2:
                return float(v)
    return None
