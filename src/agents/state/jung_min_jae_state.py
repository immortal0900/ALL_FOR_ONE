from utils.util import attach_auto_keys
from typing import Annotated, TypedDict, Optional, Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from agents.state.analysis_state import ANALYSIS_OUTPUTS_SCHEMA


@attach_auto_keys
class JungMinJaeState(TypedDict):

    start_input: dict
    rag_context: Optional[str]
    final_draft: Optional[str]
    final_report: Optional[str]

    # think_tool 결과
    review_feedback: Optional[str]
    segment: int
    segment_buffers: Dict[str, str]
    messages: Annotated[list[AnyMessage], add_messages]

    analysis_outputs: dict
    """키 구조는 ANALYSIS_OUTPUTS_SCHEMA 상수를 참조하세요."""