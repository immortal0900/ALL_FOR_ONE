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
import contextlib
import contextvars
from typing import Optional

from dotenv import load_dotenv

# 현재 활성 세션 ID를 비동기/스레드 안전하게 전파하는 ContextVar.
# asyncio.create_task() 및 run_in_executor() 호출 시 자동으로 복사되므로
# LangGraph 노드 함수들이 config를 명시적으로 전달하지 않아도 session_id가 유지됩니다.
_active_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "langfuse_session_id", default=None
)

# 현재 활성 태그를 전파하는 ContextVar.
# set_test_context()에서 설정하면 merge_config()가 모든 LLM 호출에 태그를 자동 주입합니다.
# 이 ContextVar가 없으면 평가 LLM 호출(DeepEval gpt-5-mini)에 태그를 붙일 방법이 없어
# Langfuse 대시보드에서 테스트 trace와 프로덕션 trace를 구분할 수 없습니다.
_active_tags: contextvars.ContextVar[Optional[list]] = contextvars.ContextVar(
    "langfuse_tags", default=None
)

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
            # Langfuse 3.x: CallbackHandler 생성자는 session_id를 직접 받지 않음.
            # session_id는 session_context()의 propagate_attributes()를 통해
            # SDK 내부적으로 자동 전파됩니다.
            # Ref: https://langfuse.com/docs/integrations/langchain/tracing
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

        [메모리 흐름 — 리스트인 경우]
        existing_config = {"callbacks": [tool_callback]}
                                    ↓ merge
        merged_config   = {"callbacks": [tool_callback, langfuse_handler]}

        [메모리 흐름 — AsyncCallbackManager인 경우]
        existing_config = {"callbacks": AsyncCallbackManager(...)}
                                    ↓ add_handler
        merged_config   = {"callbacks": AsyncCallbackManager(handlers=[..., langfuse_handler])}

        [주의]
        AsyncCallbackManager를 리스트에 넣으면([manager, handler]) langchain-core가
        매니저 객체를 일반 handler로 취급하여 .run_inline 등의 속성에 접근 시
        AttributeError가 발생합니다. 반드시 add_handler()로 등록해야 합니다.

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

        raw_callbacks = merged.get("callbacks")

        # LangGraph가 전달하는 AsyncCallbackManager/CallbackManager 처리
        # 매니저 객체를 리스트에 넣으면 langchain-core가 handler로 오인하여 크래시
        # 따라서 매니저의 add_handler()를 통해 직접 등록
        try:
            from langchain_core.callbacks.manager import (
                AsyncCallbackManager,
                CallbackManager,
            )
            if isinstance(raw_callbacks, (AsyncCallbackManager, CallbackManager)):
                raw_callbacks.add_handler(handler)
                return merged
        except ImportError:
            pass

        # 일반 리스트인 경우: 기존 리스트에 handler 추가
        if isinstance(raw_callbacks, (list, tuple)):
            existing_callbacks = list(raw_callbacks)
        elif raw_callbacks is not None:
            existing_callbacks = [raw_callbacks]
        else:
            existing_callbacks = []

        # 기존 콜백 리스트에 이미 Langfuse CallbackHandler가 있는지 확인하여 중복 방지
        if self._callback_handler_class and not any(isinstance(c, self._callback_handler_class) for c in existing_callbacks):
            existing_callbacks.append(handler)

        merged["callbacks"] = existing_callbacks

        # ContextVar에 session_id/tags가 설정되어 있으면 metadata에 자동 주입.
        # [존재 이유]
        # RetryableChatOpenAI._merge_langfuse_config()는 merge_config()만 호출하므로
        # session_id/tags를 전달할 경로가 없었습니다.
        # ContextVar → metadata 자동 주입으로 set_test_context()에서 설정한 값이
        # 모든 LLM 호출의 trace에 반영됩니다.
        # setdefault()를 사용하여 기존 config에 명시적으로 설정된 값은 덮어쓰지 않습니다.
        session_id = _active_session_id.get(None)
        tags = _active_tags.get(None)
        if session_id or tags:
            metadata = merged.setdefault("metadata", {})
            if session_id:
                metadata.setdefault("langfuse_session_id", session_id)
            if tags:
                metadata.setdefault("langfuse_tags", tags)

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

    def update_observation(self, **kwargs):
        """현재 활성화된 관찰(observation) 객체에 데이터를 추가합니다.
        
        @observe 데코레이터로 감싸진 함수 내부에서 호출하여
        입출력 텍스트, 토큰 사용량(usage), 메타데이터 등을 기록합니다.

        [동작 원리]
        get_client().update_current_generation() 를 사용하여
        현재 실행 컨텍스트의 generation 단위에 안전하게 접근합니다.
        @observe(as_type="generation") 으로 감싸진 함수 내부에서 호출됩니다.
        """
        if not self._enabled:
            return

        try:
            # Langfuse 3.x: langfuse.decorators 모듈 삭제됨.
            # get_client().update_current_generation()으로 대체.
            # Ref: https://langfuse.com/docs/sdk/python
            client = self.get_client()
            if client is not None:
                client.update_current_generation(**kwargs)
        except Exception as e:
            logger.debug("Langfuse update_observation 실패 (무시 가능): %s", e)

    @contextlib.asynccontextmanager
    async def session_context(self, session_id: str):
        """세션 ID를 하위 모든 관찰 객체(@observe)에 전파하는 비동기 컨텍스트 매니저.

        [존재 이유]
        LangChain의 config metadata 방식만으로는 @observe 로 감싸진 외부 도구
        (Gemini, Perplexity 통신 등)까지 세션 ID가 안정적으로 전달되지 않습니다.
        이 블록으로 실행부를 감싸면 모든 하위 호출이 같은 세션으로 묶입니다.

        [변경 이유: contextmanager → asynccontextmanager]
        동기 CM에서 비동기 코드(await graph.ainvoke())를 감쌀 경우,
        OpenTelemetry의 ContextVar 토큰이 다른 async Context에서 생성되어
        detach 시 ValueError("was created in a different Context") 발생.
        async CM으로 변경하여 async 경계를 올바르게 처리합니다.
        Ref: https://langfuse.com/docs/observability/features/sessions

        [구조 설계: setup → yield → cleanup]
        - setup(import + __enter__)은 yield 전에 실행. 실패 시 pa=None으로 안전 진행.
        - yield 후 예외(athrow)는 잡지 않고 그대로 전파 (재yield 금지).
        - finally에서 cleanup만 수행.
        이전 구조에서 except ImportError/Exception 블록이 athrow 후 재yield하여
        "RuntimeError: generator didn't stop after athrow()" 발생했음.

        [Graceful Degradation]
        비활성화 시 내부 동작 없이 안전하게 yield 합니다.
        """
        if not self._enabled:
            yield
            return

        # ContextVar에 session_id를 저장하여 get_callback_handler() 호출 시
        # 자동으로 주입되도록 합니다.
        token = _active_session_id.set(session_id)

        # --- Setup: yield 전에 초기화 시도, 실패 시 pa=None ---
        pa = None
        try:
            from langfuse import propagate_attributes

            # propagate_attributes()는 동기 전용 CM(sync-only context manager)이므로
            # async 함수 내에서 with 문으로 사용하면 OpenTelemetry ContextVar 토큰이
            # 다른 async Context에서 생성/해제되어 "Failed to detach context" 발생.
            # __enter__()로 컨텍스트를 설정하고, __exit__()의 detach 실패는 finally에서 무시.
            pa = propagate_attributes(session_id=session_id)
            pa.__enter__()
        except Exception as e:
            logger.debug("Langfuse session_context 초기화 실패 (무시 가능): %s", e)

        # --- Yield: 단일 yield 지점. 예외는 호출부로 그대로 전파됨 ---
        try:
            yield
        finally:
            # --- Cleanup: propagate_attributes 해제 + ContextVar 리셋 ---
            if pa is not None:
                try:
                    pa.__exit__(None, None, None)
                except Exception:
                    pass  # async 경계의 ContextVar 토큰 불일치 — 무해한 경고
            _active_session_id.reset(token)

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

    def set_test_context(
        self,
        session_id: str,
        tags: Optional[list] = None,
    ) -> tuple:
        """동기 환경(pytest 등)에서 session_id와 tags를 ContextVar에 설정합니다.

        [존재 이유]
        기존 session_context()는 async-only 컨텍스트 매니저이므로
        동기적으로 실행되는 pytest fixture에서 사용할 수 없습니다.
        이 메서드는 ContextVar를 직접 설정하여 동일한 효과를 제공합니다.

        [데이터 흐름]
        set_test_context(session_id, tags)
          → _active_session_id.set(session_id)
          → _active_tags.set(tags)
          → 이후 merge_config() 호출 시 metadata에 자동 주입
          → Langfuse trace에 session_id + tags 기록

        Args:
            session_id: Langfuse 세션 ID (예: "deepeval-20260321-154507")
            tags: Langfuse 태그 목록 (예: ["deepeval", "evaluation"])

        Returns:
            (session_token, tags_token) 튜플 — clear_test_context()에 전달하여
            ContextVar를 원래 값으로 복원합니다.
        """
        session_token = _active_session_id.set(session_id)
        tags_token = _active_tags.set(tags)

        # Langfuse SDK의 propagate_attributes()도 동기적으로 설정
        # @observe 데코레이터로 감싸진 외부 도구 호출까지 session_id 전파
        self._propagate_ctx = None
        if self._enabled:
            try:
                from langfuse import propagate_attributes
                self._propagate_ctx = propagate_attributes(session_id=session_id)
                self._propagate_ctx.__enter__()
            except Exception as e:
                logger.debug("propagate_attributes 설정 실패 (무시 가능): %s", e)

        logger.info("테스트 컨텍스트 설정: session_id=%s, tags=%s", session_id, tags)
        return (session_token, tags_token)

    def clear_test_context(self, tokens: tuple) -> None:
        """set_test_context()에서 반환된 토큰으로 ContextVar를 원래 값으로 복원합니다.

        Args:
            tokens: set_test_context()가 반환한 (session_token, tags_token) 튜플
        """
        session_token, tags_token = tokens

        # propagate_attributes 해제
        if self._propagate_ctx is not None:
            try:
                self._propagate_ctx.__exit__(None, None, None)
            except Exception:
                pass  # ContextVar 토큰 불일치 — 무해한 경고
            self._propagate_ctx = None

        _active_session_id.reset(session_token)
        _active_tags.reset(tags_token)
        logger.info("테스트 컨텍스트 해제 완료")


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------
# 모듈 임포트 시 1회만 생성됩니다.
# 사용법: from utils.langfuse_tracker import tracker
# ---------------------------------------------------------------------------
tracker = TokenTracker()
