"""
LangGraph 기반 Housing FAQ 챗봇 에이전트 래퍼
"""
from typing import List, Dict, Any, Optional
import uuid

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))

from chatbot_graph_agent import chatbot_graph


class HousingChatAgentLangGraph:
    """LangGraph 기반 주택 FAQ 챗봇 에이전트"""

    def __init__(self):
        self.graph = chatbot_graph
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}

    def _get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """세션별 대화 기록 가져오기"""
        return self.conversation_history.get(session_id, [])

    def _update_conversation_history(self, session_id: str, role: str, content: str):
        """대화 기록 업데이트"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        self.conversation_history[session_id].append({"role": role, "content": content})
        # 최근 10개 메시지만 유지
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]

    def chat(
        self,
        message: str,
        target_area: Optional[str] = None,
        main_type: Optional[str] = None,
        total_units: Optional[str] = None,
        session_id: Optional[str] = None,
        use_faq: bool = True,
        use_rule: bool = True,
        use_policy: bool = True,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        챗봇 대화 처리 (LangGraph 사용)

        Args:
            message: 사용자 메시지
            target_area: 사업지 장소
            main_type: 단지 타입
            total_units: 세대수
            session_id: 세션 ID
            use_faq: FAQ 데이터 사용 여부
            use_rule: 주택공급 규칙 데이터 사용 여부
            use_policy: 정책 데이터 사용 여부

        Returns:
            (응답 메시지, 참조 문서 리스트)
        """
        # 세션 ID 생성
        if not session_id:
            session_id = str(uuid.uuid4())

        # 초기 상태 구성
        initial_state = {
            "user_message": message,
            "target_area": target_area or "",
            "main_type": main_type or "",
            "total_units": total_units or "",
            "session_id": session_id,
            "use_faq": use_faq,
            "use_rule": use_rule,
            "use_policy": use_policy,
            "faq_context": [],
            "rule_context": [],
            "policy_context": [],
            "source_docs": [],
            "messages": [],
            "response": "",
            "sources": [],
        }

        from utils.langfuse_tracker import tracker
        
        # 외부 도구(Gemini, Perplexity)까지 세션 ID를 전파하기 위해 session_context 사용
        with tracker.session_context(session_id=session_id):
            result = self.graph.invoke(initial_state)

        answer = result["response"]
        sources = result["sources"]

        # 대화 기록 업데이트
        if session_id:
            self._update_conversation_history(session_id, "user", message)
            self._update_conversation_history(session_id, "assistant", answer)

        return answer, sources

    async def stream_chat(
        self,
        message: str,
        target_area: Optional[str] = None,
        main_type: Optional[str] = None,
        total_units: Optional[str] = None,
        session_id: Optional[str] = None,
        use_faq: bool = True,
        use_rule: bool = True,
        use_policy: bool = True,
    ):
        """
        스트리밍 챗봇 대화 처리 (LangGraph 사용)

        Args:
            message: 사용자 메시지
            target_area: 사업지 장소
            main_type: 단지 타입
            total_units: 세대수
            session_id: 세션 ID
            use_faq: FAQ 데이터 사용 여부
            use_rule: 주택공급 규칙 데이터 사용 여부
            use_policy: 정책 데이터 사용 여부

        Yields:
            응답 청크
        """
        # 세션 ID 생성
        if not session_id:
            session_id = str(uuid.uuid4())

        # 초기 상태 구성
        initial_state = {
            "user_message": message,
            "target_area": target_area or "",
            "main_type": main_type or "",
            "total_units": total_units or "",
            "session_id": session_id,
            "use_faq": use_faq,
            "use_rule": use_rule,
            "use_policy": use_policy,
            "faq_context": [],
            "rule_context": [],
            "policy_context": [],
            "source_docs": [],
            "messages": [],
            "response": "",
            "sources": [],
        }

        # 그래프 스트리밍 실행
        full_response = ""
        sources = []

        # 외부 도구(Gemini, Perplexity)까지 세션 ID를 전파하기 위해 session_context 사용
        from utils.langfuse_tracker import tracker
        
        with tracker.session_context(session_id=session_id):
            async for event in self.graph.astream_events(initial_state, version="v2"):
                kind = event["event"]
    
                # LLM 스트리밍 이벤트 처리
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_response += content
                        yield {"type": "text", "content": content}
    
                # 최종 상태 처리
                elif kind == "on_chain_end":
                    if "output" in event["data"]:
                        output = event["data"]["output"]
                        if "sources" in output:
                            sources = output["sources"]

        # 대화 기록 업데이트
        if session_id:
            self._update_conversation_history(session_id, "user", message)
            self._update_conversation_history(session_id, "assistant", full_response)

        # 소스 전송
        yield {"type": "sources", "sources": sources}
        yield {"type": "done"}

    def clear_history(self, session_id: str):
        """특정 세션의 대화 기록 삭제"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]
