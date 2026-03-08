# utils/langfuse_tracker.py
"""
Langfuse 토큰/비용 추적 공통 유틸리티.

공식 문서: https://langfuse.com/docs/integrations/langchain/tracing

[존재 이유]
이 모듈이 없으면 28개 LLM 호출 지점마다 CallbackHandler 초기화 코드를
개별적으로 작성해야 합니다. TokenTracker 싱글톤을 통해 DRY 원칙을 지키면서
모든 호출 지점에서 동일한 추적 패턴을 사용합니다.

[아키텍처 위치]
utils/llm.py (RetryableChatOpenAI) → langfuse_tracker.py (콜백 제공)
tools/gemini_search_tool.py       → langfuse_tracker.py (수동 추적)
tools/perplexity_search_tool.py   → langfuse_tracker.py (수동 추적)

[Graceful Degradation 설계]
LANGFUSE_ENABLED=false 이거나 langfuse 패키지가 미설치된 환경에서도
기존 시스템은 정상 작동합니다. 모든 메서드가 안전한 기본값(None, {})을 반환합니다.
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TokenTracker:
    """Langfuse 토큰/비용 추적을 위한 싱글톤 유틸리티.

    [메모리 흐름]
    1. 서버 시작 시 TokenTracker 인스턴스 1개 생성
    2. RetryableChatOpenAI.invoke() 호출 때마다 get_callback_handler() 호출
    3. CallbackHandler가 LLM 호출 정보를 Langfuse 서버로 비동기 전송
    4. 서버 종료 시 flush() → shutdown() 으로 잔여 이벤트 전송

    [Graceful Degradation]
    _enabled=False 일 때 모든 메서드는 빈 값을 반환하므로
    호출부 코드에서 if 분기가 필요 없습니다.
    """

    def __init__(self):
        """Langfuse 클라이언트 초기화.

        환경변수 LANGFUSE_ENABLED가 'true'이고 langfuse 패키지가
        설치되어 있을 때만 활성화됩니다.
        """
        self._enabled = False
        self._callback_handler_class = None
        self._get_client_func = None
        self._observe_func = None

        # 환경변수로 활성화 여부 결정
        langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower()
        if langfuse_enabled != "true":
            logger.info("Langfuse tracking disabled (LANGFUSE_ENABLED != 'true')")
            return

        # langfuse 패키지 import 시도 (미설치 시 안전하게 비활성화)
        try:
            from langfuse.langchain import CallbackHandler
            from langfuse import get_client, observe

            self._callback_handler_class = CallbackHandler
            self._get_client_func = get_client
            self._observe_func = observe
            self._enabled = True
            logger.info("Langfuse tracking enabled")

        except ImportError:
            logger.warning(
                "langfuse 패키지가 설치되지 않았습니다. "
                "추적을 활성화하려면: pip install langfuse"
            )
        except Exception as e:
            logger.warning("Langfuse 초기화 실패 (무시 가능): %s", e)

    @property
    def is_enabled(self) -> bool:
        """Langfuse 추적 활성화 여부."""
        return self._enabled

    def get_callback_handler(self):
        """LangChain용 CallbackHandler 인스턴스를 반환합니다.

        [존재 이유]
        이 메서드가 없으면 RetryableChatOpenAI에서 직접 langfuse를 import하고
        CallbackHandler를 생성해야 합니다. 이는 Graceful Degradation을 깨뜨리고
        langfuse 미설치 환경에서 ImportError를 발생시킵니다.

        Returns:
            CallbackHandler 인스턴스 (비활성화 시 None)
        """
        if not self._enabled:
            return None

        try:
            return self._callback_handler_class()
        except Exception as e:
            logger.warning("CallbackHandler 생성 실패: %s", e)
            return None

    def get_langfuse_config(
        self,
        tags: Optional[list] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """LangChain .invoke() 호출에 전달할 config 딕셔너리를 생성합니다.

        [데이터 흐름]
        이 config dict → chain.invoke(input, config=config)
                       → CallbackHandler가 trace에 tags/session_id/user_id 기록
                       → Langfuse 대시보드에서 필터링 가능

        Args:
            tags:       trace에 붙일 태그 목록 (예: ["policy", "report"])
            session_id: 사용자 세션 ID (대시보드에서 세션별 그룹화)
            user_id:    사용자 ID (대시보드에서 사용자별 그룹화)
            metadata:   추가 메타데이터 딕셔너리

        Returns:
            LangChain config dict. 비활성화 시 빈 dict.
        """
        if not self._enabled:
            return {}

        handler = self.get_callback_handler()
        if handler is None:
            return {}

        config = {"callbacks": [handler]}

        # metadata 필드를 통해 trace attribute 전달
        # 공식 문서: langfuse_user_id, langfuse_session_id, langfuse_tags
        # https://langfuse.com/docs/integrations/langchain/tracing#trace-attributes
        langfuse_metadata = {}
        if user_id:
            langfuse_metadata["langfuse_user_id"] = user_id
        if session_id:
            langfuse_metadata["langfuse_session_id"] = session_id
        if tags:
            langfuse_metadata["langfuse_tags"] = tags
        if metadata:
            langfuse_metadata.update(metadata)

        if langfuse_metadata:
            config["metadata"] = langfuse_metadata

        return config

    def merge_config(self, existing_config: Optional[dict] = None) -> Optional[dict]:
        """기존 LangChain config에 Langfuse 콜백을 안전하게 병합합니다.

        [존재 이유]
        LangGraph의 ToolNode 등이 내부적으로 자체 callbacks를 config에 전달합니다.
        기존 callbacks를 덮어쓰면 도구 호출이 실패하므로, 반드시 append 방식으로
        병합해야 합니다.

        [메모리 흐름]
        existing_config = {"callbacks": [tool_callback]}
                                    ↓ merge
        merged_config   = {"callbacks": [tool_callback, langfuse_handler]}

        Args:
            existing_config: 기존 LangChain config (None 가능)

        Returns:
            Langfuse 콜백이 병합된 config. 비활성화 시 existing_config 그대로 반환.
        """
        if not self._enabled:
            return existing_config

        handler = self.get_callback_handler()
        if handler is None:
            return existing_config

        # 기존 config가 없으면 새로 생성
        if existing_config is None:
            return {"callbacks": [handler]}

        # 기존 config를 복사하여 원본 보호
        merged = dict(existing_config)

        # 기존 callbacks 리스트에 langfuse handler 추가 (덮어쓰기 금지)
        # LangGraph 내부에서 callbacks로 AsyncCallbackManager 객체를 전달할 수 있으므로
        # list/tuple이 아닌 경우 새 리스트로 감싸서 TypeError 방지
        raw_callbacks = merged.get("callbacks", [])
        if isinstance(raw_callbacks, (list, tuple)):
            existing_callbacks = list(raw_callbacks)
        else:
            # AsyncCallbackManager 등 이터러블이 아닌 객체가 들어온 경우
            existing_callbacks = [raw_callbacks]
        existing_callbacks.append(handler)
        merged["callbacks"] = existing_callbacks

        return merged

    def observe(self, *args, **kwargs):
        """Langfuse @observe 데코레이터를 반환합니다.

        네이티브 API 호출(Gemini, Perplexity)에 사용합니다.

        [사용법]
        @tracker.observe(as_type="generation")
        def my_llm_call(...):
            ...

        비활성화 시 identity 데코레이터를 반환하여 원본 함수를 그대로 실행합니다.
        """
        if not self._enabled or self._observe_func is None:
            # 비활성화 시 아무 동작도 하지 않는 identity 데코레이터
            def identity_decorator(func):
                return func
            return identity_decorator

        return self._observe_func(*args, **kwargs)

    def get_client(self):
        """Langfuse 클라이언트를 반환합니다.

        네이티브 API 호출의 수동 추적에서 usage_details, cost_details를
        업데이트할 때 사용합니다.

        Returns:
            Langfuse 클라이언트 인스턴스. 비활성화 시 None.
        """
        if not self._enabled or self._get_client_func is None:
            return None

        try:
            # 함수 실행 결과 반환
            return self._get_client_func()
        except Exception as e:
            logger.warning("Langfuse 클라이언트 조회 실패: %s", e)
            return None

    def flush(self):
        """보류 중인 이벤트를 Langfuse 서버로 전송합니다.

        [존재 이유]
        Langfuse SDK는 이벤트를 내부 큐에 버퍼링합니다.
        요청 처리 완료 시 flush()를 호출하지 않으면
        일부 이벤트가 유실될 수 있습니다.
        """
        client = self.get_client()
        if client is not None:
            try:
                client.flush()
            except Exception as e:
                logger.warning("Langfuse flush 실패: %s", e)

    def shutdown(self):
        """Langfuse 클라이언트를 종료합니다.

        서버 종료 시 호출하여 잔여 이벤트를 전송하고
        리소스를 정리합니다.
        """
        client = self.get_client()
        if client is not None:
            try:
                client.shutdown()
            except Exception as e:
                logger.warning("Langfuse shutdown 실패: %s", e)


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------
# 모듈 임포트 시 1회만 생성됩니다.
# 사용법: from utils.langfuse_tracker import tracker
# ---------------------------------------------------------------------------
tracker = TokenTracker()
