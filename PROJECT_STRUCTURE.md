# ALL-FOR-ONE 프로젝트 구조 및 규칙 가이드

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [전체 아키텍처](#전체-아키텍처)
3. [폴더 구조 및 역할](#폴더-구조-및-역할)
4. [핵심 규칙 및 컨벤션](#핵심-규칙-및-컨벤션)
5. [폴더 간 연결 관계](#폴더-간-연결-관계)
6. [워크플로우 흐름](#워크플로우-흐름)
7. [개발 가이드라인](#개발-가이드라인)

---

## 프로젝트 개요

**ALL-FOR-ONE**은 부동산 보고서 작성을 위한 멀티에이전트 리서치 시스템입니다.

### 주요 기능
- **7개의 병렬 분석 에이전트**: 입지, 정책, 수급, 미분양, 인구, 주변시세, 청약FAQ 분석
- **보고서 작성 에이전트**: 분석 결과를 종합하여 최종 보고서 생성
- **RAG 시스템**: 문서 파싱 및 벡터 스토어 기반 정보 검색
- **웹 검색 통합**: Perplexity API를 통한 실시간 정보 수집

---

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Main Agent                           │
│  (시작 확인 → 입력 파싱 → 분석 → 보고서 작성 → 완료)      │
└─────────────────────────────────────────────────────────┘
                        │
                        ├─────────────────┐
                        │                 │
                        ▼                 ▼
        ┌───────────────────────┐  ┌─────────────────┐
        │   Analysis Graph      │  │ Jung Min Jae    │
        │   (7개 병렬 에이전트)   │  │ Agent           │
        └───────────────────────┘  └─────────────────┘
                │
                ├─ Location Insight Agent
                ├─ Policy Agent
                ├─ Supply Demand Agent
                ├─ Unsold Insight Agent
                ├─ Population Insight Agent
                ├─ Nearby Market Agent
                └─ Housing FAQ Agent
```

### 워크플로우 단계
1. **START_CONFIRMATION**: 사용자 입력 확인 및 추가 질문 수집
2. **ANALYSIS**: 7개 분석 에이전트 병렬 실행
3. **JUNG_MIN_JAE**: 분석 결과를 종합하여 보고서 작성
4. **RENDERING**: PDF 생성 (구현 예정)
5. **DONE**: 완료

---

## 폴더 구조 및 역할

### 루트 디렉토리
```
ALL-FOR-ONE/
├── src/                    # 모든 소스 코드
├── pyproject.toml         # 프로젝트 설정 및 의존성
├── README.md              # 프로젝트 설명 및 세팅 가이드
└── .env                   # 환경 변수 (gitignore 필수)
```

### src/agents/ - 에이전트 관리
**역할**: LangGraph 기반 멀티에이전트 워크플로우 정의

#### agents/state/
- **start_state.py**: 초기 입력 상태 정의 (`StartInput`, `StartConfirmation`)
- **main_state.py**: 메인 워크플로우 상태 (`MainState`)
- **analysis_state.py**: 분석 에이전트들 상태 정의 (7개)
- **jung_min_jae_state.py**: 보고서 작성 에이전트 상태

**규칙**: 
- 모든 State 클래스는 `@attach_auto_keys` 데코레이터 필수
- State는 `TypedDict` 또는 `BaseModel`로 정의
- 상태 키 접근은 `StateClass.KEY.key_name` 형식 사용

#### agents/main/
- **main_agent.py**: 전체 워크플로우 오케스트레이션
  - `start_confirmation()`: 시작 여부 확인
  - `start()`: 사용자 입력 파싱
  - `analysis_graph_node()`: 분석 그래프 호출
  - `jung_min_jae_graph()`: 보고서 작성 그래프 호출

#### agents/analysis/
- **analysis_graph.py**: 7개 분석 에이전트 병렬 실행 그래프
- **location_insight_agent.py**: 입지 분석 (교통, POI, 개발호재)
- **policy_agent.py**: 경제/정책 분석 (금리, 규제)
- **supply_demand_agent.py**: 공급/수요 분석 (시계열)
- **unsold_insight_agent.py**: 미분양 분석
- **population_insight_agent.py**: 인구 분석 (연령, 이동)
- **nearby_market_agent.py**: 주변 시세/경쟁 분석
- **housing_faq_agent.py**: 청약 규칙/FAQ

**공통 패턴**:
```python
# 1. RAG 검색
def retreive(state) -> State

# 2. 웹 검색
def web_search(state) -> State

# 3. 프롬프트 설정
def analysis_setting(state) -> State

# 4. 에이전트 실행 (도구 사용 가능)
def agent(state) -> State

# 5. 라우터 (도구 호출 여부 판단)
def router(state) -> str
```

#### agents/jung_min_jae/
- **jung_min_jae_agent.py**: 최종 보고서 작성 에이전트
  - 세그먼트별 작성 (3개 세그먼트)
  - 이전 세그먼트 요약 생성
  - 자체 검증 도구 (`think_tool`)

---

### src/prompts/ - 프롬프트 관리
**역할**: 모든 LLM 프롬프트를 YAML 파일로 중앙 관리

#### 파일 구조
- **PromptType.py**: 프롬프트 타입 Enum 정의
  - 각 프롬프트는 `(이름, 경로, 설명)` 튜플로 정의
  - 경로는 `get_project_root()` 사용

- **PromptMananger.py**: 프롬프트 로더 및 관리자
  - YAML 파일에서 프롬프트 로드
  - `input_variables` 기반 변수 치환

- **YAML 파일들**:
  - `main.yaml`: 메인 에이전트 프롬프트
  - `analysis_*.yaml`: 각 분석 에이전트 프롬프트
  - `jung_min_jae.yaml`: 보고서 작성 프롬프트

#### 사용법 규칙
```python
# 1단계: PromptType에서 프롬프트 선택
# 2단계: YAML 파일 확인 → input_variables 확인
# 3단계: PromptManager 사용

prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt(
    messages=messages_str,  # YAML의 input_variables에 정의된 변수들
    target_area=target_area,
    date=get_today_str()
)
```

---

### src/tools/ - 도구 관리
**역할**: 에이전트가 사용하는 도구들 정의

#### tools/rag/ - RAG 시스템
- **db_collection_name.py**: 벡터 스토어 컬렉션 이름 상수
  - `AGE_POPULATION_KEY`: 연령별 인구 데이터
  - `MOVE_PEOPLE_KEY`: 인구 이동 데이터

- **document_loader/**: 문서 파싱
  - `default_loader.py`: PDF, DOC 등 다양한 형식 지원
  - `csv_loader.py`: CSV 파일 로더

- **chunker/**: 문서 청킹
  - `default_chunker.py`: 기본 청킹 전략
  - `maxmin_checker.py`: 최소/최대 길이 검증

- **retriever/**: 벡터 검색
  - `age_population_retriever.py`: 연령별 인구 리트리버
  - `housing_faq_retriever.py`: 청약 FAQ 리트리버

- **indexing/**: 인덱싱 스크립트 (Jupyter 노트북)
  - 데이터를 벡터 스토어에 인덱싱하는 작업

#### tools/mcp/ - MCP 클라이언트
- **mcp_client.py**: MCP (Model Context Protocol) 클라이언트
  - Exa 검색 등 외부 MCP 서버 연동
  - 싱글톤 패턴으로 클라이언트 관리

#### tools/ - 개별 도구들
- **kostat_api.py**: 통계청 API 도구
- **kakao_api_distance_tool.py**: 카카오 지도 API (거리 계산)
- **maps.py**: 지도 생성 도구
- **house_sale_volume_tool.py**: 매매 거래량 조회
- **housing_supply_tool.py**: 주택 공급 현황 조회
- 기타 다양한 데이터 수집 도구들

**규칙**: 
- 각 도구는 `@tool` 데코레이터 사용
- docstring에 사용법, 매개변수, 반환값 명시

---

### src/data/ - 데이터 파일
**역할**: PDF, CSV, Excel 등 원본 데이터 저장

#### 폴더 구조
- **economic_metrics/**: 경제 지표 데이터
- **housing_pre_promise/**: 청약 관련 문서
- **policy_factors/**: 정책 관련 문서
- **population_insight/**: 인구 데이터
- **supply_demand/**: 공급/수요 데이터
- **unsold_units/**: 미분양 데이터

**규칙**: 
- 모든 데이터는 `src/data/` 하위에 저장
- `get_data_dir()` 유틸 함수로 경로 접근

---

### src/utils/ - 유틸리티
**역할**: 공통 유틸리티 함수들

- **util.py**: 
  - `attach_auto_keys`: State 클래스에 KEY 클래스 자동 주입
  - `get_project_root()`: 프로젝트 루트 경로 반환
  - `get_data_dir()`: 데이터 디렉토리 경로 반환
  - `get_today_str()`: 날짜 문자열 생성

- **llm.py**: 
  - `LLMProfile`: LLM 프로필 및 인스턴스 관리
    - `dev_llm()`: 개발용
    - `chat_bot_llm()`: 챗봇용
    - `analysis_llm()`: 분석용 (reasoning_effort="high")
    - `report_llm()`: 보고서 작성용

- **format_message.py**: 
  - Rich 라이브러리를 사용한 메시지 포맷팅
  - 디버깅 및 로깅용

---

### src/lab/ - 연구소
**역할**: 테스트 및 실험 코드

**규칙**: 
- 프로젝트와 무관한 테스트 코드도 OK
- `.ipynb`와 `.py` 버전 모두 사용 가능

---

## 핵심 규칙 및 컨벤션

### 1. State 관리 규칙

**필수 데코레이터**:
```python
from utils.util import attach_auto_keys

@attach_auto_keys
class MyState(TypedDict):
    field1: str
    field2: int
```

**키 접근 방법**:
```python
# ✅ 올바른 방법
field1_key = MyState.KEY.field1
value = state[field1_key]

# ❌ 잘못된 방법
value = state["field1"]  # 직접 문자열 사용 금지
```

### 2. 프롬프트 사용 규칙

**3단계 프로세스**:
1. `PromptType`에서 프롬프트 선택
2. YAML 파일 열어서 `input_variables` 확인
3. `PromptManager`로 프롬프트 가져오기

```python
# 예시
prompt = PromptManager(PromptType.LOCATION_INSIGHT_SYSTEM).get_prompt(
    messages=messages_str,  # YAML에 정의된 변수명 그대로 사용
    target_area=target_area,
    date=get_today_str()
)
```

### 3. LLM 호출 규칙

**프로필별 사용**:
- **챗봇/시작 확인**: `LLMProfile.chat_bot_llm()`
- **분석 에이전트**: `LLMProfile.analysis_llm()` (reasoning_effort="high")
- **보고서 작성**: `LLMProfile.report_llm()`
- **개발/테스트**: `LLMProfile.dev_llm()`

### 4. 도구 정의 규칙

```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def my_tool(param: str) -> str:
    """도구 설명
    
    Args:
        param: 매개변수 설명
        
    Returns:
        반환값 설명
    """
    return result
```

### 5. LangGraph 노드 규칙

**노드 함수 시그니처**:
```python
def my_node(state: MyState) -> MyState:
    # 상태 읽기
    value = state[MyState.KEY.field]
    
    # 상태 업데이트
    return {MyState.KEY.field: new_value}
```

**라우터 함수**:
```python
def router(state: MyState) -> str:
    # 조건에 따라 노드 이름 반환
    if condition:
        return "node_name"
    return "__end__"
```

### 6. 경로 관리 규칙

**항상 유틸 함수 사용**:
```python
from utils.util import get_project_root, get_data_dir

# ✅ 올바른 방법
prompt_path = Path(get_project_root()) / "src" / "prompts" / "main.yaml"
data_path = get_data_dir() / "economic_metrics" / "data.csv"

# ❌ 잘못된 방법
prompt_path = "src/prompts/main.yaml"  # 하드코딩 금지
```

---

## 폴더 간 연결 관계

### 1. Main Agent → Analysis Graph 연결

```
agents/main/main_agent.py
    │
    ├─ imports: agents.analysis.analysis_graph.analysis_graph
    ├─ state: MainState
    │   └─ analysis_outputs: Dict[str, str]
    │
    └─ calls: analysis_graph.invoke({"start_input": ...})
```

**데이터 흐름**:
- `MainState.start_input` → `AnalysisGraphState.start_input`
- `AnalysisGraphState.analysis_outputs` → `MainState.analysis_outputs`

### 2. Analysis Graph → 개별 에이전트 연결

```
agents/analysis/analysis_graph.py
    │
    ├─ imports: agents.analysis.*_agent.*_graph
    ├─ state: AnalysisGraphState
    │   ├─ start_input: dict
    │   ├─ {agent_name}_output: str
    │   └─ analysis_outputs: Dict[str, str]
    │
    └─ transform: make_transform(agent_name)
        ├─ input: {"start_input": state["start_input"]}
        └─ output: {f"{agent_name}_output": ...}
```

**각 에이전트 공통 구조**:
- `start_input` 받아서 분석 수행
- `{agent_name}_output` 생성
- `analysis_outputs`에 병합

### 3. 개별 에이전트 → Tools 연결

```
agents/analysis/location_insight_agent.py
    │
    ├─ imports: tools.kostat_api.get_move_population
    ├─ tools: [think_tool, ...]
    ├─ RAG: tools.rag.retriever.*_retriever
    ├─ Web: perplexity.Perplexity()
    └─ Prompts: prompts.PromptManager(PromptType.LOCATION_INSIGHT_*)
```

**도구 사용 패턴**:
1. RAG 검색: `retreive()` 노드에서 벡터 스토어 검색
2. 웹 검색: `web_search()` 노드에서 Perplexity API 호출
3. 도구 호출: `agent()` 노드에서 LLM이 도구 선택 → `tool_node` 실행

### 4. Analysis → Jung Min Jae 연결

```
agents/main/main_agent.py
    │
    ├─ imports: agents.jung_min_jae.jung_min_jae_agent.report_graph
    ├─ state: MainState
    │   ├─ analysis_outputs: Dict[str, str]
    │   ├─ start_input: dict
    │   └─ final_report: str
    │
    └─ calls: report_graph.invoke({
        "start_input": ...,
        "analysis_outputs": ...,
        "segment": 1
    })
```

**데이터 흐름**:
- `MainState.analysis_outputs` → `JungMinJaeState.analysis_outputs`
- `MainState.start_input` → `JungMinJaeState.start_input`
- `JungMinJaeState.final_report` → `MainState.final_report`

### 5. Prompts → Agents 연결

```
prompts/PromptType.py (Enum 정의)
    │
    ├─ 각 프롬프트 타입: (이름, 경로, 설명)
    │
prompts/PromptMananger.py
    │
    ├─ YAML 파일 로드
    ├─ input_variables 추출
    └─ 변수 치환하여 프롬프트 생성
    │
agents/analysis/*_agent.py
    │
    └─ PromptManager(PromptType.*).get_prompt(**kwargs)
```

**연결 체인**:
1. `PromptType`에서 프롬프트 선택
2. `PromptManager`로 YAML 파일 로드
3. `input_variables`에 맞춰 변수 전달
4. 에이전트의 `analysis_setting()` 노드에서 사용

### 6. Data → RAG → Agents 연결

```
data/*/
    │ (원본 데이터 파일들)
    │
tools/rag/indexing/*.ipynb
    │ (인덱싱 스크립트)
    │
    └─ PostgreSQL 벡터 스토어 저장
    │
tools/rag/retriever/*_retriever.py
    │
    ├─ PGVector 연결
    ├─ 컬렉션 이름: db_collection_name.*_KEY
    └─ 검색 결과 반환
    │
agents/analysis/*_agent.py
    │
    └─ retreive() 노드에서 리트리버 호출
```

**데이터 흐름**:
1. `data/` 폴더의 원본 파일
2. `tools/rag/indexing/`에서 인덱싱
3. PostgreSQL 벡터 스토어 저장
4. `tools/rag/retriever/`에서 검색
5. 에이전트의 `rag_context`에 포함

### 7. Utils → 모든 곳 연결

```
utils/util.py
    ├─ attach_auto_keys → 모든 State 클래스
    ├─ get_project_root → 프롬프트 경로, 데이터 경로
    └─ get_today_str → 프롬프트에 날짜 전달

utils/llm.py
    └─ LLMProfile → 모든 에이전트에서 LLM 인스턴스 생성

utils/format_message.py
    └─ 디버깅 및 로깅용 (선택적)
```

---

## 워크플로우 흐름

### 전체 실행 흐름

```
사용자 입력
    │
    ▼
[START_CONFIRMATION] agents/main/main_agent.py::start_confirmation
    │
    ├─ confirm=False → 사용자에게 질문 → END
    │
    └─ confirm=True → start() 노드
            │
            ▼
        [START] agents/main/main_agent.py::start
            │
            ├─ StartInput 파싱
            ├─ start_input 저장
            └─ status="ANALYSIS"
                │
                ▼
        [ANALYSIS] agents/analysis/analysis_graph.py
            │
            ├─ 7개 에이전트 병렬 실행
            │   ├─ Location Insight Agent
            │   ├─ Policy Agent
            │   ├─ Supply Demand Agent
            │   ├─ Unsold Insight Agent
            │   ├─ Population Insight Agent
            │   ├─ Nearby Market Agent
            │   └─ Housing FAQ Agent
            │
            ├─ 각 에이전트 공통 흐름:
            │   ├─ retreive() → RAG 검색
            │   ├─ web_search() → 웹 검색
            │   ├─ analysis_setting() → 프롬프트 설정
            │   ├─ agent() → LLM 실행
            │   ├─ router() → 도구 필요 여부 판단
            │   └─ tools → 도구 실행 (필요시)
            │
            └─ join_results() → analysis_outputs 병합
                │
                ▼
        [JUNG_MIN_JAE] agents/jung_min_jae/jung_min_jae_agent.py
            │
            ├─ retreiver() → RAG 검색
            ├─ reporting() → 프롬프트 설정
            ├─ agent() → 세그먼트 작성 (3회 반복)
            │   ├─ seg1 작성
            │   ├─ seg2 작성 (이전 세그먼트 요약 포함)
            │   └─ seg3 작성 (이전 세그먼트 요약 포함)
            │
            ├─ finalize_merge() → 세그먼트 병합
            ├─ review_with_think() → 자체 검증
            └─ final_report 생성
                │
                ▼
        [RENDERING] (구현 예정)
            │
            ▼
        [DONE]
```

### 개별 분석 에이전트 흐름

```
START
    │
    ├─ retreive() (병렬)
    └─ web_search() (병렬)
        │
        ├─ RAG 검색 완료
        └─ 웹 검색 완료
            │
            ▼
        analysis_setting()
            │
            ├─ System 프롬프트 로드
            ├─ Human 프롬프트 생성
            └─ messages 설정
                │
                ▼
            agent()
                │
                ├─ LLM 호출
                └─ 도구 호출 필요?
                    │
                    ├─ Yes → tools 노드
                    │   └─ agent() (재귀)
                    │
                    └─ No → END
```

---

## 개발 가이드라인

### 새로운 분석 에이전트 추가 시

1. **State 정의** (`agents/state/analysis_state.py`):
```python
@attach_auto_keys
class NewAgentState(TypedDict):
    start_input: dict
    new_agent_output: str
    rag_context: Optional[str]
    web_context: Optional[str]
    messages: Annotated[list[AnyMessage], add_messages]
```

2. **에이전트 파일 생성** (`agents/analysis/new_agent.py`):
```python
# 공통 패턴 따르기
def retreive(state) -> NewAgentState
def web_search(state) -> NewAgentState
def analysis_setting(state) -> NewAgentState
def agent(state) -> NewAgentState
def router(state) -> str
```

3. **프롬프트 추가** (`prompts/PromptType.py`):
```python
NEW_AGENT_SYSTEM = (
    "NEW_AGENT_SYSTEM",
    str(Path(get_project_root()) / "src" / "prompts" / "analysis_new_agent.yaml"),
    "새 에이전트 시스템 프롬프트",
)
```

4. **YAML 파일 생성** (`prompts/analysis_new_agent.yaml`):
```yaml
NEW_AGENT_SYSTEM:
  name: "NEW_AGENT_SYSTEM"
  prompt: |
    시스템 프롬프트 내용...
  input_variables:
    - messages
    - target_area
```

5. **Analysis Graph에 추가** (`agents/analysis/analysis_graph.py`):
```python
from agents.analysis.new_agent import new_agent_graph

new_agent_key = "new_agent"
graph_builder.add_node(new_agent_key, new_agent_graph, transform=make_transform(new_agent_key))

# join_results 함수에도 추가
analysis_outputs = {
    # ... 기존 항목들
    new_agent_key: state.get(f"{new_agent_key}_output"),
}
```

### 새로운 도구 추가 시

1. **도구 파일 생성** (`tools/my_tool.py`):
```python
from langchain_core.tools import tool

@tool(parse_docstring=True)
def my_tool(param: str) -> str:
    """도구 설명"""
    return result
```

2. **에이전트에서 사용**:
```python
from tools.my_tool import my_tool

tool_list = [think_tool, my_tool]
llm_with_tools = llm.bind_tools(tool_list)
tool_node = ToolNode(tool_list)
```

### 새로운 프롬프트 추가 시

1. **PromptType에 추가** (`prompts/PromptType.py`)
2. **YAML 파일에 정의** (기존 파일 또는 새 파일)
3. **사용처에서 PromptManager 호출**

### 환경 변수 설정

`.env` 파일 필수 항목:
```
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

---

## 중요 체크리스트

### 에이전트 개발 시
- [ ] State 클래스에 `@attach_auto_keys` 데코레이터 적용
- [ ] 상태 키 접근 시 `StateClass.KEY.key_name` 사용
- [ ] 프롬프트는 `PromptManager`를 통해 로드
- [ ] LLM 인스턴스는 `LLMProfile`에서 가져오기
- [ ] 경로는 `get_project_root()`, `get_data_dir()` 사용

### 코드 리뷰 시 확인사항
- [ ] 하드코딩된 경로 없음
- [ ] State 키 직접 문자열 사용 없음
- [ ] 프롬프트 변수명이 YAML의 `input_variables`와 일치
- [ ] 에이전트가 공통 패턴 따름 (retreive → web_search → analysis_setting → agent)

---

## 참고 자료

- **LangGraph 문서**: https://langchain-ai.github.io/langgraph/
- **LangChain 문서**: https://python.langchain.com/
- **프로젝트 README**: `README.md` 참조

---

**마지막 업데이트**: 2025년 1월
**작성자**: 화인
**목적**: 새로운 개발자가 프로젝트 구조를 빠르게 파악하고 중복 작업 방지

