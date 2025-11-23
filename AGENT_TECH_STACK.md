# 에이전트별 기술 스택 정리

## Location Insight Agent

| 기술 스택 | 용도 | 사용 위치 |
|---------|------|----------|
| LangGraph | 워크플로우 그래프 구성 (StateGraph, START, END) | 그래프 빌더 및 노드 연결 |
| LangChain Core | 도구 및 메시지 관리 (tool, SystemMessage, HumanMessage) | think_tool, 프롬프트 메시지 생성 |
| LangGraph Prebuilt | 도구 노드 실행 (ToolNode) | 도구 실행 노드 |
| LLM Profile | LLM 인스턴스 생성 및 도구 바인딩 | analysis_llm(), bind_tools() |
| Prompt Manager | 프롬프트 템플릿 관리 | LOCATION_INSIGHT_SYSTEM, LOCATION_INSIGHT_HUMAN |
| Gemini Search API | 지역 특징 및 주변 호재 검색 | gemini_search_tool 함수 |
| Perplexity Search API | 웹 검색 및 정보 검증 | perplexity_search 도구 |
| Kakao API | 주소 좌표 변환 및 거리 계산 | kakao_api_distance_tool 함수 |
| CSV 변환 | 카카오 API 결과를 CSV로 변환 | location_kakao_to_drive |
| State 관리 | 상태 관리 (LocationInsightState, StartInput) | 상태 키 정의 및 관리 |

## Nearby Market Agent

| 기술 스택 | 용도 | 사용 위치 |
|---------|------|----------|
| LangGraph | 워크플로우 그래프 구성 (StateGraph, START, END) | 그래프 빌더 및 노드 연결 |
| LangChain Core | 도구 및 메시지 관리 (tool, SystemMessage, HumanMessage) | think_tool, 프롬프트 메시지 생성 |
| LangGraph Prebuilt | 도구 노드 실행 (ToolNode) | 도구 실행 노드 |
| LLM Profile | LLM 인스턴스 생성 및 도구 바인딩 | analysis_llm(), bind_tools() |
| Prompt Manager | 프롬프트 템플릿 관리 | NEARBY_MARKET_SYSTEM, NEARBY_MARKET_HUMAN |
| JSON 파싱 | 텍스트에서 JSON 추출 및 파싱 | extract_json_from_text 함수 |
| Gemini Search API | 매매/분양 아파트 정보 검색 | gemini_search_tool 함수 |
| Perplexity Search API | 분양 정보 검증 | perplexity_search_tool 함수 |
| Kakao API | 주소 좌표 변환 및 거리 계산 | kakao_api_distance_tool 함수 |
| 실거래가 API | 매매 아파트 실거래가 조회 | get_real_estate_price_tool 함수 |
| CSV 변환 | 단지 정보를 CSV로 변환 | nearby_complexes_to_csv |
| State 관리 | 상태 관리 (NearbyMarketState, StartInput) | 상태 키 정의 및 관리 |

## Policy Agent

| 기술 스택 | 용도 | 사용 위치 |
|---------|------|----------|
| LangGraph | 워크플로우 그래프 구성 (StateGraph, START, END, add_messages) | 그래프 빌더 및 노드 연결 |
| LangChain Core | 도구 및 메시지 관리 (tool, SystemMessage, HumanMessage) | think_tool, 프롬프트 메시지 생성 |
| LangGraph Prebuilt | 도구 노드 실행 (ToolNode) | 도구 실행 노드 |
| Pydantic | 구조화된 출력 모델 정의 (BaseModel, Field) | ReportCheck 모델 정의 |
| TypedDict, Annotated | 타입 힌팅 | 상태 타입 정의 |
| LLM Profile | LLM 인스턴스 생성 및 도구 바인딩 | analysis_llm(), bind_tools(), with_structured_output() |
| Prompt Manager | 프롬프트 템플릿 관리 | POLICY_SYSTEM, POLICY_HUMAN, POLICY_COMPARISON_SEGMENT_01/02 |
| RAG (Retrieval Augmented Generation) | PDF 문서 검색 및 임베딩 (PolicyPDFRetriever) | policy_pdf_retrieve 함수 |
| 국가 정책 검색 | 국가 정책 뉴스 검색 (national_policy_retriever) | national_news 함수 |
| 웹 크롤링 | 지역 뉴스 수집 (estate_web_crawling_tool) | region_news 함수 |
| Perplexity Search API | 웹 검색 및 정보 보완 | perplexity_search 도구 |
| CSV 변환 | 뉴스 데이터를 CSV로 변환 | region_news_to_drive, netional_news_to_drive |
| Structured Output | 구조화된 출력 생성 | evaluator_llm (ReportCheck 형식) |
| State 관리 | 상태 관리 (PolicyState, StartInput, ReportCheck) | 상태 키 정의 및 관리 |
| 반복 검색 로직 | 보고서 완성도 평가 후 재검색 | evaluate_report_completeness, execute_additional_retrieval |

## 공통 기술 스택

| 기술 스택 | 용도 |
|---------|------|
| LangGraph | 모든 에이전트에서 워크플로우 그래프 구성 |
| LangChain Core | 도구 및 메시지 관리 |
| LLM Profile | LLM 인스턴스 생성 및 관리 |
| Prompt Manager | 프롬프트 템플릿 관리 |
| State 관리 | 각 에이전트별 상태 관리 |
| Tool 패턴 | think_tool을 통한 반성 및 점검 |

