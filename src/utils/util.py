import inspect
from typing import get_type_hints, TypeVar, Type, Any
from datetime import datetime
from pathlib import Path

T = TypeVar("T")


def build_tool_prompt(tools: list) -> str:
    """도구 목록을 사람이 읽기 쉬운 텍스트 형태로 변환합니다.

    Args:
        tools: LangChain tool 객체 리스트

    Returns:
        도구 이름, 시그니처, 설명이 포함된 텍스트
    """
    text = "사용 가능한 도구 목록:\n\n"
    for tool in tools:
        sig = inspect.signature(tool)  # 함수의 (a:int, b:int) 시그니처
        doc = inspect.getdoc(tool)     # """ """ 안의 docstring
        text += f"- {tool.__name__}{sig}\n  설명: {doc}\n\n"
    return text


async def process_stream(stream_generator):
    """LangGraph 스트림 이벤트를 순회하며 agent/tools 메시지를 출력합니다."""
    results = []
    try:
        async for chunk in stream_generator:
            key = list(chunk.keys())[0]

            if key == 'agent':
                # Agent 메시지의 내용을 가져옵니다.
                # 메시지가 비어있는 경우 어떤 도구를 어떻게 호출할지 정보를 가져옵니다.
                content = (
                    chunk['agent']['messages'][0].content
                    if chunk['agent']['messages'][0].content != ''
                    else chunk['agent']['messages'][0].additional_kwargs
                )
                print(f"'agent': '{content}'")

            elif key == 'tools':
                for tool_msg in chunk['tools']['messages']:
                    print(f"'tools:': '{tool_msg.content}'")

            results.append(chunk)
        return results
    except Exception as e:
        print(f'Error processing stream: {e}')
        return results


def attach_auto_keys(cls: Type[T]) -> Type[T]:
    """클래스 정의 이후 자동으로 Key 클래스를 주입합니다 (TypedDict, BaseModel, MessagesState 전부 호환)."""
    annotations: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        try:
            hints = get_type_hints(base, include_extras=True)
        except Exception:
            hints = getattr(base, "__annotations__", {})
        annotations.update(hints or {})

    if not annotations:
        annotations = {
            k: v for k, v in vars(cls).items()
            if not k.startswith("_") and not inspect.isroutine(v)
        }
    key_cls = type(
        "KEY",
        (),
        {k: k for k in annotations.keys()}
    )
    setattr(cls, "KEY", key_cls)
    return cls


def get_today_str(pattern="%Y년 %m월 %d일") -> str:
    """현재 날짜를 지정된 패턴의 문자열로 반환합니다."""
    return datetime.now().strftime(pattern)


def get_current_dir() -> Path:
    """현재 파일이 위치한 디렉토리 경로를 반환합니다."""
    return Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()


def get_project_root(marker="pyproject.toml") -> Path:
    """프로젝트 루트 디렉토리를 찾아 반환합니다.

    Docker 환경(/app)을 먼저 확인하고,
    그 외에는 현재 파일 위치부터 상위로 올라가며 marker 파일을 탐색합니다.

    Args:
        marker: 프로젝트 루트를 식별하기 위한 파일명 (기본값: pyproject.toml)
    """
    # Docker 환경 체크 먼저
    docker_root = Path("/app")
    if docker_root.exists():
        marker_path = docker_root / marker
        if marker_path.exists():
            return docker_root

    # 일반적인 경우: 현재 파일에서 시작해서 부모 디렉토리들을 탐색
    cur = Path(__file__).resolve() if "__file__" in globals() else Path().resolve()

    # 현재 디렉토리부터 부모 디렉토리까지 순회
    for parent in [cur, *cur.parents]:
        marker_path = parent / marker
        if marker_path.exists():
            return parent

    # 마커 파일을 찾지 못한 경우
    # Docker 환경이면 /app 반환
    if "/app" in str(cur):
        return Path("/app")

    # 그 외의 경우 현재 작업 디렉토리 반환
    return Path.cwd()


def get_data_dir() -> Path:
    """프로젝트의 데이터 디렉토리 경로를 반환합니다."""
    return get_project_root() / "src" / "data"