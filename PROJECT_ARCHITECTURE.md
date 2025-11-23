# ALL-FOR-ONE 프로젝트 아키텍처 가이드

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [전체 워크플로우](#전체-워크플로우)
3. [폴더 구조 및 역할](#폴더-구조-및-역할)
4. [핵심 규칙 및 컨벤션](#핵심-규칙-및-컨벤션)
5. [폴더 간 연결 관계](#폴더-간-연결-관계)
6. [상태 관리 시스템](#상태-관리-시스템)
7. [프롬프트 관리 시스템](#프롬프트-관리-시스템)
8. [도구(Tools) 구조](#도구tools-구조)
9. [데이터 관리](#데이터-관리)

---

## 프로젝트 개요

**ALL-FOR-ONE**은 부동산 리서치 보고서 작성을 위한 멀티에이전트 시스템입니다.

### 주요 특징
- **LangGraph 기반**: 상태 기반 워크플로우 관리
- **7개 분석 에이전트**: 병렬 실행으로 다양한 관점 분석
- **1개 보고서 작성 에이전트**: 분석 결과를 종합하여 최종 보고서 작성
- **RAG 지원**: PostgreSQL + pgvector를 활용한 벡터 검색
- **YAML 기반 프롬프트 관리**: 중앙화된 프롬프트 관리 시스템

---

## 전체 워크플로우

```
사용자 입력
    ↓
[Main Agent] start_confirmation
    ├─ confirm=False → END (추가 질문)
    └─ confirm=True → start
        ↓
[Analysis Graph] 병렬 실행 (7개 에이전트)
    ├─ LocationInsightAgent (입지분석)
    ├─ EconomicInsightAgent (경제/정책)
    ├─ SupplyDemandAgent (수급분석)
    ├─ UnsoldInsightAgent (미분양분석)
    ├─ PopulationInsightAgent (인구분석)
    ├─ NearbyMarketAgent (주변시세)
    └─ HousingFAQAgent (청약규칙)
        ↓
    join_results (결과 병합)
        ↓
[JungMinJae Agent] 보고서 작성
    ├─ retreiver (RAG 컨텍스트 조회)
    ├─ reporting (프롬프트 설정)
    ├─ agent (LLM 호출)
    ├─ router (세그먼트별 반복: seg1→seg2→seg3)
    ├─ finalize_merge (세그먼트 병합)
    └─ review_with_think (자체 검증)
        ↓
최종 보고서 완성
```

### 상태 전이
```
START_CONFIRMATION → ANALYSIS → JUNG_MIN_JAE → RENDERING → DONE
```

---

## 폴더 구조 및 역할

### 루트 디렉토리
```
RAG_COMMANDER/
├── pyproject.toml          # 프로젝트 설정 및 의존성
├── README.md               # 프로젝트 가이드
├── .env                     # 환경 변수 (API 키 등)
├── uv.lock                  # 의존성 잠금 파일
└── src/                     # 소스 코드 (모든 코드는 여기)
```

### src/ 폴더 구조

```
src/
├── agents/                  # 에이전트 관리 (핵심 워크플로우)
│   ├── main/               # 메인 에이전트 (전체 워크플로우 조율)
│   │   └── main_agent.py   # START → ANALYSIS → JUNG_MIN_JAE 흐름
│   ├── analysis/           # 1단계: 분석 에이전트 모음 (병렬 실행)
│   │   ├── analysis_graph.py         # 7개 분석 에이전트 병렬 실행
│   │   ├── location_insight_agent.py # 입지분석
│   │   ├── policy_agent.py           # 경제/정책 분석
│   │   ├── supply_demand_agent.py    # 수급분석
│   │   ├── unsold_insight_agent.py    # 미분양분석
│   │   ├── population_insight_agent.py # 인구분석
│   │   ├── nearby_market_agent.py    # 주변시세
│   │   └── housing_faq_agent.py      # 청약규칙
│   ├── jung_min_jae/       # 2단계: 보고서 작성 에이전트
│   │   └── jung_min_jae_agent.py     # 분석 결과 종합 → 보고서 작성
│   └── state/              # LangGraph 상태 정의
│       ├── main_state.py              # 메인 워크플로우 상태
│       ├── analysis_state.py          # 분석 에이전트 상태들
│       ├── jung_min_jae_state.py      # 보고서 작성 상태
│       └── start_state.py             # 시작 입력 스키마 (Pydantic)
│
├── prompts/                # 프롬프트 관리 (YAML 파일)
│   ├── PromptType.py       # 프롬프트 타입 Enum 정의
│   ├── PromptMananger.py   # 프롬프트 로더 및 관리자
│   ├── main.yaml           # 메인 에이전트 프롬프트
│   ├── analysis_*.yaml     # 각 분석 에이전트별 프롬프트
│   └── jung_min_jae.yaml   # 보고서 작성 에이전트 프롬프트
│
├── tools/                  # 에이전트의 도구(Tools)
│   ├── rag/                # RAG 관련 도구
│   │   ├── db_collection_name.py      # 컬렉션 이름 상수
│   │   ├── document_loader/           # 문서 로더 (CSV, PDF 등)
│   │   ├── chunker/                   # 문서 청킹 전략
│   │   ├── indexing/                  # 벡터 인덱싱 노트북
│   │   └── retriever/                 # 검색기 (Retriever)
│   ├── mcp/                # MCP (Model Context Protocol) 클라이언트
│   ├── kostat_api.py       # 통계청 API 도구
│   ├── maps.py             # 지도/좌표 관련 도구
│   ├── kakao_api_distance_tool.py # 카카오 거리 계산
│   └── ...                 # 기타 도구들
│
├── data/                   # 데이터 파일 저장소
│   ├── economic_metrics/   # 경제 지표 데이터
│   ├── housing_pre_promise/ # 청약 관련 문서
│   ├── policy_factors/     # 정책 관련 문서
│   ├── population_insight/ # 인구 데이터
│   ├── supply_demand/      # 수급 데이터
│   └── unsold_units/       # 미분양 데이터
│
├── utils/                  # 유틸리티 함수
│   ├── util.py             # attach_auto_keys, 경로 유틸 등
│   ├── llm.py              # LLM 프로필 관리
│   └── format_message.py   # 메시지 포맷팅
│
└── lab/                    # 연구소 (테스트/실험 코드)
    ├── *.ipynb             # Jupyter 노트북
    └── *.py                # 테스트 스크립트
```

---

## 핵심 규칙 및 컨벤션

### 1. 프롬프트 사용법

#### Step 1: PromptType Enum에서 선택
```python
from prompts import PromptType

# 예: LOCATION_INSIGHT_SYSTEM 선택
prompt_type = PromptType.LOCATION_INSIGHT_SYSTEM
```

#### Step 2: YAML 파일 확인
- 경로: `src/prompts/analysis_location_insight.yaml`
- `input_variables` 확인 (예: `messages`, `target_area` 등)

#### Step 3: PromptManager로 프롬프트 가져오기
```python
from prompts import PromptManager, PromptType

prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt(
    messages=messages_str,  # input_variables에 맞춰 매핑
    target_area="인천광역시 부평구..."
)
```

**⚠️ 중요**: `input_variables`에 정의된 모든 변수를 `get_prompt()`에 전달해야 함

---

### 2. LangGraph 상태 키 사용법

#### Step 1: 상태 클래스에 `@attach_auto_keys` 데코레이터 추가
```python
from utils.util import attach_auto_keys
from typing import TypedDict

@attach_auto_keys
class LocationInsightState(TypedDict):
    start_input: dict
    location_insight_output: Optional[str]
    messages: Annotated[list[AnyMessage], add_messages]
```

#### Step 2: 상태 파일 상단에서 키 상수 정의
```python
output_key = LocationInsightState.KEY.location_insight_output
start_input_key = LocationInsightState.KEY.start_input
messages_key = LocationInsightState.KEY.messages
```

#### Step 3: 노드 함수에서 사용
```python
def agent(state: LocationInsightState) -> LocationInsightState:
    start_input = state[start_input_key]  # ✅ 안전한 키 접근
    return {output_key: "결과"}
```

**⚠️ 중요**: 
- 문자열 하드코딩 금지 (`state["start_input"]` ❌)
- `State.KEY.필드명` 패턴 사용 (`state[State.KEY.필드명]` ✅)

---

### 3. LLM 호출법

#### LLMProfile 클래스 사용
```python
from utils.llm import LLMProfile

# 개발용
dev_llm = LLMProfile.dev_llm()

# 챗봇용
chat_llm = LLMProfile.chat_bot_llm()

# 분석용 (high reasoning)
analysis_llm = LLMProfile.analysis_llm()

# 보고서 작성용
report_llm = LLMProfile.report_llm()
```

**⚠️ 중요**: 각 용도에 맞는 LLM 사용
- 분석: `analysis_llm()` (reasoning_effort="high")
- 보고서: `report_llm()` (일반)
- 챗봇: `chat_bot_llm()` (사용자 인터랙션)

---

### 4. Tools 폴더 사용법

#### 파일 네이밍 규칙
- 테스트용: `*.ipynb` (Jupyter 노트북)
- 프로덕션용: `*.py` (Python 스크립트)

**예시**:
```
tools/
├── maps.ipynb      # 테스트용
└── maps.py         # 프로덕션용
```

#### Tool 생성 규칙
```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def my_tool(param: str) -> str:
    """도구 설명 (docstring이 자동으로 프롬프트에 포함됨)
    
    Args:
        param: 파라미터 설명
        
    Returns:
        반환값 설명
    """
    return "결과"
```

---

## 폴더 간 연결 관계

### 1. Main Agent → Analysis Graph

**연결 파일**:
- `src/agents/main/main_agent.py` → `src/agents/analysis/analysis_graph.py`

**데이터 흐름**:
```python
# main_agent.py
def analysis_graph_node(state: MainState) -> MainState:
    result = analysis_graph.invoke({
        "start_input": deepcopy(state[start_input_key])
    })
    return {
        "analysis_outputs": result.get("analysis_outputs", {}),
        status_key: "JUNG_MIN_JAE"
    }
```

**상태 매핑**:
- `MainState.start_input` → `AnalysisGraphState.start_input`
- `AnalysisGraphState.analysis_outputs` → `MainState.analysis_outputs`

---

### 2. Analysis Graph → 개별 Analysis Agent

**연결 파일**:
- `src/agents/analysis/analysis_graph.py` → 각 `*_agent.py`

**데이터 흐름**:
```python
# analysis_graph.py
def make_transform(agent_name: str):
    return {
        "input": lambda s: {"start_input": deepcopy(s.get("start_input", {}))},
        "output": lambda sub_s: {
            f"{agent_name}_output": sub_s.get(f"{agent_name}_output", "")
        },
    }

graph_builder.add_node(
    location_insight_key, 
    location_insight_graph, 
    transform=make_transform(location_insight_key)
)
```

**상태 매핑**:
- `AnalysisGraphState.start_input` → 각 Agent의 `State.start_input`
- 각 Agent의 `State.{agent}_output` → `AnalysisGraphState.{agent}_output`

---

### 3. Main Agent → JungMinJae Agent

**연결 파일**:
- `src/agents/main/main_agent.py` → `src/agents/jung_min_jae/jung_min_jae_agent.py`

**데이터 흐름**:
```python
# main_agent.py
def jung_min_jae_graph(state: MainState) -> MainState:
    result = report_graph.invoke({
        "start_input": deepcopy(state[start_input_key]),
        "analysis_outputs": deepcopy(state[analysis_outputs_key]),
        "segment": 1
    })
    return {
        "final_report": result["final_report"],
        status_key: "RENDERING"
    }
```

**상태 매핑**:
- `MainState.start_input` → `JungMinJaeState.start_input`
- `MainState.analysis_outputs` → `JungMinJaeState.analysis_outputs`
- `JungMinJaeState.final_report` → `MainState.final_report`

---

### 4. Prompts → Agents

**연결 파일**:
- `src/prompts/PromptType.py` → 각 `*_agent.py`

**데이터 흐름**:
```python
# location_insight_agent.py
from prompts import PromptManager, PromptType

system_prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt()
human_prompt = PromptManager(PromptType.LOCATION_INSIGHT_HUMAN).get_prompt(
    target_area=target_area,
    scale=scale,
    ...
)
```

**파일 매핑**:
- `PromptType.LOCATION_INSIGHT_SYSTEM` → `src/prompts/analysis_location_insight.yaml`
- `PromptType.MAIN_START` → `src/prompts/main.yaml`
- `PromptType.JUNG_MIN_JAE_SYSTEM` → `src/prompts/jung_min_jae.yaml`

---

### 5. Tools → Agents

**연결 파일**:
- `src/tools/*.py` → 각 `*_agent.py`

**사용 예시**:
```python
# location_insight_agent.py
from tools.kostat_api import get_move_population
from tools.kakao_api_distance_tool import calculate_distance

# 또는 ToolNode로 바인딩
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

tool_list = [think_tool, get_move_population, calculate_distance]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)
```

---

### 6. RAG (Retriever) → Agents

**연결 파일**:
- `src/tools/rag/retriever/*.py` → 각 `*_agent.py`

**사용 예시**:
```python
# location_insight_agent.py
from tools.rag.retriever.housing_faq_retriever import retriever_housing_faq

def retreive(state: LocationInsightState) -> LocationInsightState:
    retriever = retriever_housing_faq()
    query = json.dumps(start_input, ensure_ascii=False)
    result = retriever.invoke(query)
    return {rag_context_key: result}
```

**데이터 흐름**:
- `State.start_input` → Retriever Query
- Retriever Results → `State.rag_context`
- `State.rag_context` → Prompt (`LOCATION_INSIGHT_HUMAN` 등)

---

### 7. Data → Tools/RAG

**연결 파일**:
- `src/data/*/` → `src/tools/rag/indexing/*.ipynb`
- `src/data/*/` → `src/tools/*.py` (CSV/Excel 로더)

**인덱싱 예시**:
```python
# tools/rag/indexing/age_population_indexing.ipynb
from tools.rag.document_loader.csv_loader import load_csv
from utils.util import get_data_dir

data_path = get_data_dir() / "population_insight" / "연령별인구현황.csv"
documents = load_csv(data_path)
# 벡터 스토어에 인덱싱
```

**컬렉션 이름 매핑**:
- `tools/rag/db_collection_name.py`에 상수 정의
- 예: `AGE_POPULATION_KEY = "AGE_POPULATION"`

---

## 상태 관리 시스템

### 1. MainState (`src/agents/state/main_state.py`)

**역할**: 전체 워크플로우 상태 관리

**필드**:
```python
@attach_auto_keys
class MainState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # 사용자 메시지
    start_input: dict                                      # 사용자 입력 정보
    analysis_outputs: Dict[str, str]                       # 7개 분석 결과
    final_report: Optional[str]                           # 최종 보고서
    logs: list[str]                                        # 로그
    status: Literal[
        "START_CONFIRMATION",
        "ANALYSIS",
        "JUNG_MIN_JAE",
        "RENDERING",
        "DONE"
    ]
```

---

### 2. AnalysisGraphState (`src/agents/state/analysis_state.py`)

**역할**: 분석 에이전트들의 병렬 실행 상태 관리

**필드**:
```python
@attach_auto_keys
class AnalysisGraphState(TypedDict, total=False):
    analysis_outputs: Annotated[Dict[str, str], operator.or_]  # 병합 결과
    location_insight_output: str
    economic_insight_output: str
    housing_faq_output: str
    nearby_market_output: str
    population_insight_output: str
    supply_demand_output: str
    unsold_insight_output: str
    start_input: Annotated[dict, operator.or_]  # 모든 에이전트에 공유
```

**개별 Agent State 예시**:
```python
@attach_auto_keys
class LocationInsightState(TypedDict):
    start_input: dict
    location_insight_output: Optional[str]
    rag_context: Optional[str]
    web_context: Optional[str]
    messages: Annotated[list[AnyMessage], add_messages]
    my_tool: str
```

---

### 3. JungMinJaeState (`src/agents/state/jung_min_jae_state.py`)

**역할**: 보고서 작성 에이전트 상태 관리

**필드**:
```python
@attach_auto_keys
class JungMinJaeState(TypedDict):
    analysis_outputs: dict              # 7개 분석 결과
    start_input: dict                   # 사용자 입력
    rag_context: Optional[str]          # RAG 컨텍스트
    final_report: Optional[str]         # 최종 보고서
    review_feedback: Optional[str]       # 자체 검증 피드백
    segment: int                        # 현재 세그먼트 (1, 2, 3)
    segment_buffers: Dict[str, str]     # 세그먼트별 버퍼
    messages: Annotated[list[AnyMessage], add_messages]
```

---

### 4. StartInput (`src/agents/state/start_state.py`)

**역할**: 사용자 입력 스키마 (Pydantic BaseModel)

**필드**:
```python
@attach_auto_keys
class StartInput(BaseModel):
    target_area: str                    # 조사 대상 주소
    scale: str                          # 단지 규모
    total_units: Optional[int]         # 전체 세대수
    units_by_type: Optional[str]       # 타입별 세대수
    brand: Optional[str]               # 브랜드/시공사
    orientation: Optional[str]         # 향/배치
    parking_ratio: Optional[float]     # 주차시설 비율
    terrain_condition: Optional[str]   # 지형조건
    gross_area: Optional[float]        # 연면적
    floor_area_ratio_range: Optional[float]      # 용적률
    building_coverage_ratio_range: Optional[float] # 건폐율
```

---

## 프롬프트 관리 시스템

### 1. PromptType Enum (`src/prompts/PromptType.py`)

**역할**: 모든 프롬프트 타입 정의

**구조**:
```python
class PromptType(Enum):
    def __init__(self, value, path, description):
        self._value_ = value
        self.path = path          # YAML 파일 경로
        self.description = description
    
    LOCATION_INSIGHT_SYSTEM = (
        "LOCATION_INSIGHT_SYSTEM",
        str(Path(get_project_root()) / "src" / "prompts" / "analysis_location_insight.yaml"),
        "입지 분석 에이전트의 시스템 메시지",
    )
```

**⚠️ 중요**: 새 프롬프트 추가 시 `PromptType`에 Enum 추가 필수

---

### 2. PromptManager (`src/prompts/PromptMananger.py`)

**역할**: YAML 파일 로드 및 프롬프트 템플릿 관리

**사용법**:
```python
prompt_manager = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM)
prompt = prompt_manager.get_prompt(
    messages=messages_str,
    target_area="인천광역시..."
)
```

**YAML 구조**:
```yaml
LOCATION_INSIGHT_SYSTEM:
  name: LOCATION_INSIGHT_SYSTEM
  prompt: |
    [역할]
    당신은...
  input_variables:
    - messages
    - target_area
```

**⚠️ 중요**: 
- `input_variables`에 정의된 모든 변수 전달 필수
- 누락 시 `ValueError` 발생

---

## 도구(Tools) 구조

### 1. RAG 도구 (`src/tools/rag/`)

**구조**:
```
rag/
├── db_collection_name.py      # 컬렉션 이름 상수
├── document_loader/            # 문서 로더
│   ├── csv_loader.py
│   └── default_loader.py
├── chunker/                   # 청킹 전략
│   ├── default_chunker.py
│   └── maxmin_checker.py
├── indexing/                  # 인덱싱 노트북
│   ├── age_population_indexing.ipynb
│   └── move_population_indexing.ipynb
└── retriever/                 # 검색기
    ├── age_population_retriever.py
    └── housing_faq_retriever.py
```

**사용 흐름**:
1. 데이터 준비: `src/data/*/` → CSV/PDF/Excel
2. 인덱싱: `indexing/*.ipynb` 실행 → PostgreSQL 벡터 스토어 저장
3. 검색: `retriever/*.py` → 에이전트에서 호출

---

### 2. API 도구 (`src/tools/`)

**주요 도구**:
- `kostat_api.py`: 통계청 API
- `kakao_api_distance_tool.py`: 카카오 거리 계산
- `maps.py`: 지도/좌표
- `molit_search_tool.py`: 국토부 데이터
- `estate_web_crawling_tool.py`: 웹 크롤링

**사용 예시**:
```python
from tools.kostat_api import get_move_population

result = get_move_population(
    region="인천광역시",
    year=2024
)
```

---

## 데이터 관리

### 데이터 디렉토리 구조

```
src/data/
├── economic_metrics/      # 경제 지표 (CSV, Excel)
├── housing_pre_promise/   # 청약 관련 문서 (PDF, DOC)
├── policy_factors/        # 정책 문서 (PDF, Excel, JSON)
├── population_insight/    # 인구 데이터 (CSV, Excel)
├── supply_demand/         # 수급 데이터 (CSV, Excel)
└── unsold_units/          # 미분양 데이터 (CSV)
```

### 데이터 접근

```python
from utils.util import get_data_dir

data_path = get_data_dir() / "population_insight" / "인구이동_전출입_2024년.csv"
```

---

## 환경 변수 (.env)

**필수 설정**:
```env
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=false
TAVILY_API_KEY=...
OPENAI_API_KEY=...
R_ONE_API_KEY=...
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/ragdb
MCP_KEY=...
PERPLEXITY_API_KEY=...
ANTHROPIC_API_KEY=...
```

**옵션**:
```env
MATHPIX_API_KEY=...
MATHPIX_API_ID=...
```

---

## 개발 가이드라인

### 1. 새 분석 에이전트 추가 시

1. **상태 정의** (`src/agents/state/analysis_state.py`)
   ```python
   @attach_auto_keys
   class NewAgentState(TypedDict):
       start_input: dict
       new_agent_output: str
       rag_context: Optional[str]
       messages: Annotated[list[AnyMessage], add_messages]
   ```

2. **에이전트 구현** (`src/agents/analysis/new_agent.py`)
   ```python
   from agents.state.analysis_state import NewAgentState
   # ... 에이전트 로직
   ```

3. **분석 그래프에 추가** (`src/agents/analysis/analysis_graph.py`)
   ```python
   new_agent_key = "new_agent"
   graph_builder.add_node(
       new_agent_key, 
       new_agent_graph, 
       transform=make_transform(new_agent_key)
   )
   ```

4. **프롬프트 추가** (`src/prompts/analysis_new_agent.yaml`)
5. **PromptType에 추가** (`src/prompts/PromptType.py`)

---

### 2. 새 도구 추가 시

1. **도구 구현** (`src/tools/new_tool.py`)
   ```python
   from langchain_core.tools import tool
   
   @tool(parse_docstring=True)
   def new_tool(param: str) -> str:
       """도구 설명"""
       return "결과"
   ```

2. **에이전트에서 사용**
   ```python
   from tools.new_tool import new_tool
   tool_list = [new_tool]
   llm_with_tools = llm.bind_tools(tool_list)
   ```

---

### 3. 새 프롬프트 추가 시

1. **YAML 파일 생성** (`src/prompts/new_prompt.yaml`)
   ```yaml
   NEW_PROMPT_TYPE:
     name: NEW_PROMPT_TYPE
     prompt: |
       프롬프트 내용...
     input_variables:
       - var1
       - var2
   ```

2. **PromptType에 추가** (`src/prompts/PromptType.py`)
   ```python
   NEW_PROMPT_TYPE = (
       "NEW_PROMPT_TYPE",
       str(Path(get_project_root()) / "src" / "prompts" / "new_prompt.yaml"),
       "설명",
   )
   ```

3. **사용**
   ```python
   prompt = PromptManager(PromptType.NEW_PROMPT_TYPE).get_prompt(
       var1=value1,
       var2=value2
   )
   ```

---

## 체크리스트: 새 기능 추가 시

- [ ] 상태 클래스에 `@attach_auto_keys` 데코레이터 추가
- [ ] 상태 키를 상수로 정의 (`State.KEY.필드명`)
- [ ] 프롬프트는 `PromptType` Enum에 추가
- [ ] YAML 파일에 `input_variables` 정의
- [ ] `PromptManager`로 프롬프트 로드
- [ ] LLM은 용도에 맞는 `LLMProfile` 사용
- [ ] 도구는 `@tool` 데코레이터 사용
- [ ] 데이터 접근은 `get_data_dir()` 사용
- [ ] 프로젝트 루트 접근은 `get_project_root()` 사용

---

## 요약: 핵심 연결 관계

```
사용자 입력
    ↓
MainState (start_input)
    ↓
AnalysisGraphState (7개 병렬 실행)
    ├─ 각 Agent State → PromptManager → YAML
    ├─ 각 Agent State → Tools
    └─ 각 Agent State → RAG Retriever → PostgreSQL
    ↓
MainState (analysis_outputs)
    ↓
JungMinJaeState
    ├─ PromptManager → jung_min_jae.yaml
    └─ 세그먼트별 반복 (seg1→seg2→seg3)
    ↓
MainState (final_report)
```

---

**마지막 업데이트**: 2025년 1월
**작성자**: 화인

