# utils/sanitize.py
"""
ReAct 루프 출력에서 think_tool 반성문 누출을 제거하는 유틸리티.

[존재 이유]
think_tool을 사용하는 agent(nearby_market, supply_demand, unsold_insight)에서
LLM 비결정성으로 인해 최종 response.content에 think_tool(reflection: "...") 텍스트가
그대로 노출될 수 있음. 이 함수가 없으면 최종 보고서에 내부 반성문이 섞여 분석 구조가 파괴됨.
"""

import re


def strip_think_tool(text: str) -> str:
    """response.content에서 think_tool(reflection: "...") 호출 텍스트를 제거합니다.

    Args:
        text: LLM의 response.content 원본 텍스트

    Returns:
        think_tool 호출 패턴이 제거된 깨끗한 텍스트
    """
    # think_tool(reflection: "...") 패턴 제거 (이스케이프된 따옴표 포함)
    cleaned = re.sub(
        r'think_tool\(reflection:\s*"(?:[^"\\]|\\.)*"\)',
        '',
        text,
    )
    # 연속 빈 줄 정리
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()
