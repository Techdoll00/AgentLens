"""40-item golden test set for AgentLens.

A deliberately adversarial set designed to catch specific failure modes:
- 10 Happy path (baseline)
- 6 Ambiguity recognition (does it ask vs guess?)
- 6 Brand/memory sensitivity (cross-customer contamination)
- 10 Retrieval governance (NOT-logic, color disambiguation, zero-result)
- 8 State continuity (multi-turn, session switching, asset binding)

Each case includes expected stage graph + checkpoints + blocker conditions.
"""

from __future__ import annotations

from src.core.models import CaseCategory, EvalCase


def build_golden_set() -> list[EvalCase]:
    """Build the full 40-item golden test set."""
    cases: list[EvalCase] = []

    # === Happy Path (10) ===
    happy_queries = [
        ("解释一下深蓝色牛仔裤的材质组成", ["vision", "brand", "memory", "search", "ppt"],
         ["深蓝", "棉", "牛仔裤"], None, None),
        ("推荐一款适合夏季的白色T恤", ["vision", "brand", "memory", "search", "ppt"],
         ["白色", "T恤", "夏季"], None, None),
        ("这个品牌有什么经典的款式", ["vision", "brand", "memory", "search", "ppt"],
         ["经典", "款式"], None, None),
        ("帮我找一下适合商务场合的外套", ["vision", "brand", "memory", "search", "ppt"],
         ["商务", "外套"], None, None),
        ("看看这个PDF里的服装款式分析", ["vision", "brand", "memory", "search", "ppt"],
         ["服装", "分析"], None, None),
        ("根据品牌风格生成一个销售方案PPT", ["vision", "brand", "memory", "search", "ppt"],
         ["销售", "PPT", "方案"], None, None),
        ("推荐和这张图片相似的单品", ["vision", "brand", "memory", "search", "ppt"],
         ["相似", "单品"], None, None),
        ("这个客户的品牌调性是什么", ["vision", "brand", "memory", "search", "ppt"],
         ["品牌", "调性"], None, None),
        ("找一些运动风格的上衣", ["vision", "brand", "memory", "search", "ppt"],
         ["运动", "上衣"], None, None),
        ("生成这个品牌的新品推荐PPT", ["vision", "brand", "memory", "search", "ppt"],
         ["新品", "推荐", "PPT"], None, None),
    ]
    for i, (q, stages, kws, brand, not_cond) in enumerate(happy_queries, 1):
        cases.append(EvalCase(
            case_id=f"c_{i:04d}",
            query=q,
            expected_stage_graph=stages,
            expected_response_keywords=kws,
            category=CaseCategory.HAPPY_PATH,
        ))

    # === Ambiguity Recognition (6) ===
    ambiguity_queries = [
        ("找一些好看的", "好看"),
        ("给我推荐衣服", "衣服"),
        ("有没有适合的", "适合"),
        ("我想要那种感觉的单品", "感觉"),
        ("给我看看", None),
        ("有没有那种风格", "风格"),
    ]
    for i, (q, missing) in enumerate(ambiguity_queries, 11):
        cases.append(EvalCase(
            case_id=f"c_{i:04d}",
            query=q,
            expected_stage_graph=["vision", "brand", "memory", "search"],
            expected_response_keywords=[],
            category=CaseCategory.AMBIGUITY,
            metadata={"expected_behavior": "ask_for_clarification"},
        ))

    # === Brand / Memory Sensitivity (6) ===
    brand_queries = [
        ("BrandA的品牌风格分析", ["vision", "brand", "memory", "search", "ppt"],
         ["BrandA"], "BrandA"),
        ("BrandB的产品线有哪些", ["vision", "brand", "memory", "search"],
         ["BrandB"], "BrandB"),
        ("BrandA和BrandB的风格对比", ["vision", "brand", "memory", "search", "ppt"],
         ["BrandA", "BrandB"], "BrandA"),
        ("根据BrandC的风格推荐新品", ["vision", "brand", "memory", "search", "ppt"],
         ["BrandC", "新品"], "BrandC"),
        ("BrandA的视觉识别系统", ["vision", "brand", "memory", "search"],
         ["BrandA", "视觉"], "BrandA"),
        ("调取BrandB的历史销售数据", ["vision", "brand", "memory", "search", "ppt"],
         ["BrandB", "销售"], "BrandB"),
    ]
    for i, (q, stages, kws, brand) in enumerate(brand_queries, 17):
        cases.append(EvalCase(
            case_id=f"c_{i:04d}",
            query=q,
            expected_stage_graph=stages,
            expected_response_keywords=kws,
            category=CaseCategory.BRAND_SENSITIVITY,
            sensitive_brand=brand,
            forbidden_keywords=[b for b in ["BrandA", "BrandB", "BrandC"] if b != brand][:1],
        ))

    # === Retrieval Governance (10) ===
    retrieval_queries = [
        ("找不是麻材质的上衣", "麻"),
        ("找不是纯棉的外套", "纯棉"),
        ("查找深蓝色（不是浅蓝）的牛仔裤", "浅蓝"),
        ("找麻灰色的面料（注意是麻灰不是麻）", "麻"),
        ("80%棉的衣服推荐", None),
        ("不要墨绿色的羽绒服", "墨绿"),
        ("排除藏青色之外的裤子", "藏青"),
        ("找卡其色（非黑色）的裙子", None),
        ("查找深灰色与浅灰色的区别", None),
        ("找不含涤纶的天然材质", "涤纶"),
    ]
    for i, (q, not_cond) in enumerate(retrieval_queries, 23):
        kws = [kw for kw in ["麻灰", "深蓝", "80%棉", "卡其", "深灰", "浅灰"] if kw in q]
        cases.append(EvalCase(
            case_id=f"c_{i:04d}",
            query=q,
            expected_stage_graph=["vision", "brand", "memory", "search"],
            expected_response_keywords=kws,
            category=CaseCategory.RETRIEVAL_GOVERNANCE,
            not_condition=not_cond,
        ))

    # === State Continuity (8) ===
    state_queries = [
        ("上次对话提到的品牌再推荐几款", ["vision", "brand", "memory", "search", "ppt"],
         ["品牌", "推荐"], None),
        ("刚才查到的那个SKU的详细信息", ["vision", "brand", "memory", "search"],
         ["SKU", "详情"], None),
        ("切换到BrandB，重新搜索", ["vision", "brand", "memory", "search"],
         ["BrandB"], "BrandB"),
        ("记住这个品牌，下次也按这个风格推荐", ["vision", "brand", "memory", "search"],
         ["记住", "品牌"], None),
        ("对比刚刚两款的区别", ["vision", "brand", "memory", "search"],
         ["对比", "区别"], None),
        ("把上次的结果导出为PPT", ["vision", "brand", "memory", "search", "ppt"],
         ["PPT", "导出"], None),
        ("换个风格重新生成", ["vision", "brand", "memory", "search", "ppt"],
         ["风格", "生成"], None),
        ("继续我们刚才未完的对话", ["vision", "brand", "memory", "search"],
         ["继续", "对话"], None),
    ]
    for i, (q, stages, kws, brand) in enumerate(state_queries, 33):
        cases.append(EvalCase(
            case_id=f"c_{i:04d}",
            query=q,
            expected_stage_graph=stages,
            expected_response_keywords=kws,
            category=CaseCategory.STATE_CONTINUITY,
            sensitive_brand=brand,
        ))

    assert len(cases) == 40, f"Expected 40 cases, got {len(cases)}"
    return cases


def get_case_map(cases: list[EvalCase]) -> dict[str, str]:
    """Build case_id → query mapping for report display."""
    return {c.case_id: c.query for c in cases}