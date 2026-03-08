from pydantic import BaseModel, Field
from tools.rag.document_loader.csv_loader import load_csv_loader
from utils.util import get_project_root
from utils.llm import LLMProfile

class PlanningMoveItem(BaseModel):
    입주예정월: int = Field(description="예: 202601")
    지역: str = Field(description="예: 서울")
    사업유형: str = Field(description="예: 분양 또는 임대")
    주소: str = Field(description="전체 주소")
    주택명: str = Field(description="아파트/주택 단지명")
    세대수: int = Field(description="총 세대수")

class PlanningMoveResponse(BaseModel):
    items: list[PlanningMoveItem]

def planning_move_retrieve(query):
    path = get_project_root() /"src"/"data"/"supply_demand"/"250829_입주예정물량 공개용.csv"
    docs = load_csv_loader(path, encoding='utf-8', autodetect_encoding=True).load()
    
    llm = LLMProfile.dev_llm().with_structured_output(PlanningMoveResponse)
    
    response = llm.invoke(
        f"""
        주어진 데이터에서 주소가 '{query}'의 자치구(예: 강동구, 강서구 등)와 일치하는 항목만 추출해주세요.
        정확히 해당하는 자치구의 데이터만 추출하고, 결과가 없다면 빈 리스트를 반환하세요.
        
        데이터:
        {docs}
        """
    )
    
    # context_to_csv.py에서 DataFrame을 만들기 쉽도록 dict의 리스트로 반환
    return [item.model_dump() for item in response.items]
    