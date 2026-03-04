"""
정책 에이전트에서 사용하는 타입 정의
순환 import를 피하기 위해 별도 파일로 분리
"""

from pydantic import BaseModel, Field


class ReportCheck(BaseModel):
    """
    보고서가 템플릿을 충족했는지 나타내는 구조화된 평가 결과
    """

    is_complete: bool = Field(description="모든 필수 항목이 채워졌으면 True")
    missing_sections: list[str] = Field(
        default_factory=list,
        description="템플릿의 필수 목차 중 아예 내용이 비어있는 섹션 이름들의 리스트"
    )
    missing_information: str = Field(
        default="",
        description="섹션은 존재하지만, 그 안에서 구체적으로 어떤 데이터(예: 'LTV 수치가 누락됨')가 부족한지에 대한 상세 설명"
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="부족한 정보를 채우기 위해 검색 엔진이나 PDF 리트리버에 입력할 '최적화된 검색어' 리스트"
    )

