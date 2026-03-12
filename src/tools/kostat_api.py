import os
import time
import requests


class SgisAPI:
    access_token = None
    token_expire = 0  # timestamp

    @classmethod
    def get_access_token(cls):
        """토큰이 만료되었으면 새로 발급받고, 아니면 캐시된 토큰을 반환"""
        # if cls.access_token and time.time() < cls.token_expire:
        #     return cls.access_token

        AUTH_URL = "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json"
        KOSIS_CONSUMER_KEY = os.getenv("KOSIS_CONSUMER_KEY")
        KOSIS_CONSUMER_SECRET_KEY = os.getenv("KOSIS_CONSUMER_SECRET_KEY")

        params = {
            "consumer_key": KOSIS_CONSUMER_KEY,
            "consumer_secret": KOSIS_CONSUMER_SECRET_KEY,
        }

        response = requests.get(AUTH_URL, params=params)
        data = response.json()

        if data.get("errCd") == 0:
            cls.access_token = data["result"]["accessToken"]
            cls.token_expire = time.time() + 3500  # 1시간(3600초) - 안전하게 3500초
            return cls.access_token
        else:
            raise Exception(f"❌ 토큰 발급 실패: {data}")
    @classmethod
    def request_api(cls, url: str, params: dict):
        token = cls.get_access_token()
        params["accessToken"] = token

        res = requests.get(url, params=params)
        print(f"[SGIS] 요청 URL: {res.url}")
        print(f"[SGIS] 응답 코드: {res.status_code}")
        
        # 1️⃣ 빈 응답 or HTML 대응
        if not res.text.strip():
            raise RuntimeError("⚠️ SGIS 응답이 비어 있습니다. 서버 점검 중이거나 요청 파라미터 오류입니다.")
        if res.text.strip().startswith("<html"):
            raise RuntimeError(f"⚠️ SGIS에서 HTML 반환: {res.text[:200]}")

        # 2️⃣ JSON 파싱 시도
        try:
            data = res.json()
        except Exception as e:
            print("⚠️ JSONDecodeError 발생, 응답본문 일부:", res.text[:200])
            raise

        # 3️⃣ accessToken 만료 대응
        if (
            data.get("errCd") == -100
            and "accesstoken" in str(data.get("errMsg", "")).lower()
        ):
            print("⚠️ accessToken 만료됨 → 재발급 중...")
            cls.access_token = None
            token = cls.get_access_token()
            params["accessToken"] = token
            res = requests.get(url, params=params)
            data = res.json()

        # 4️⃣ SGIS 자체 오류 코드 처리
        if data.get("errCd") != 0:
            print(f"⚠️ SGIS 오류 발생: {data}")
            raise RuntimeError(f"SGIS 오류: {data}")

        return data



adm_dict = {
    "종로구": "11010",
    "중구": "11020",
    "용산구": "11030",
    "성동구": "11040",
    "광진구": "11050",
    "동대문구": "11060",
    "중랑구": "11070",
    "성북구": "11080",
    "강북구": "11090",
    "도봉구": "11100",
    "노원구": "11110",
    "은평구": "11120",
    "서대문구": "11130",
    "마포구": "11140",
    "양천구": "11150",
    "강서구": "11160",
    "구로구": "11170",
    "금천구": "11180",
    "영등포구": "11190",
    "동작구": "11200",
    "관악구": "11210",
    "서초구": "11220",
    "강남구": "11230",
    "송파구": "11240",
    "강동구": "11250",
}


# 10년 이상 노후도
def get_10_year_after_house(gu_address: str):
    
    llm_res = LLMProfile.dev_llm().invoke(
    f"""
    당신은 대한민국 서울특별시 자치구를 찾아주는 도우미 입니다. 
    에이전트 흐름중 사용하고 있습니다. 주소 질문에 특정 자치구만 찾아서 
    그부분만 출력해주시면 됩니다.
    [상황]
    어떠한 딕셔너리의 키값을 생성하기 위함입니다. 키값 표를 같이 참고해서 키에 해당하는 구로 수정하세요
    - 딕셔너리 -
    {adm_dict}
    
    [강력 지침]
    - 자치구 이외에 절대 다른말을 하지마세요
    - 자치구만 말씀하세요
    
    [예시]
    1. "서울특별시 종로구" -> "종로구"
    2. "서울 강동구 서초동" -> "강남구"
    3. "서울특별시 송파구 석촌동" -> "송파구"
    
    질문: {gu_address}
    """
    )
    
    
    HOUSE_URL = "https://sgisapi.kostat.go.kr/OpenAPI3/stats/house.json"
    params = {
        "year": "2020",  # 기준연도 (2015~2023)
        "adm_cd": [adm_dict[llm_res.content]],  # 행정구역 코드 (서울특별시)
        "low_search": "0",
        # 10년 이상들 조회
        "const_year": ["06", "07", "08", "09", "10", "11"],
    }
    
    response = SgisAPI.request_api(HOUSE_URL, params)
    return response["result"]
    
# return [{"house_cnt":"63298"}]
    

# 1인당 GDP 조회
def get_one_people_gdp():
    # https://spot.wooribank.com/pot/Dream?withyou=FXXRT0016
    # 우리은행 외환센터 연도별 기준 (송금 수신, 발신의 중간값)
    exchange_rate = {
        "2018": 1100,
        "2019": 1160,
        "2020": 1180,
        "2021": 1140,
        "2022": 1290,
        "2023": 1310,
        "2024": 1360,
    }

    one_people_gdp_dollar = {
        "2018": 33447,
        "2019": 31902,
        "2020": 31721,
        "2021": 35125,
        "2022": 32394,
        "2023": 33121,
        "2024": 36624,
    }

    def get_krw(exchange_rate, dollar):
        return exchange_rate * dollar

    one_people_gdp_dollar = {
        "2018": get_krw(exchange_rate["2018"], one_people_gdp_dollar["2018"]),
        "2019": get_krw(exchange_rate["2019"], one_people_gdp_dollar["2019"]),
        "2020": get_krw(exchange_rate["2020"], one_people_gdp_dollar["2020"]),
        "2021": get_krw(exchange_rate["2021"], one_people_gdp_dollar["2021"]),
        "2022": get_krw(exchange_rate["2022"], one_people_gdp_dollar["2022"]),
        "2023": get_krw(exchange_rate["2023"], one_people_gdp_dollar["2023"]),
        "2024": get_krw(exchange_rate["2024"], one_people_gdp_dollar["2024"]),
    }

    return one_people_gdp_dollar

def get_one_people_grdp():
    return pd.read_csv(
        get_project_root()
        / "src"
        / "data"
        / "economic_metrics"
        / "서울 자치구별 GRDP(2018-2022)-최종.csv",
        encoding="utf-8"
    )


# 각 csv 리턴  (아래는 RAG or RDB)
import pandas as pd
from utils.util import get_project_root


def get_age_population():
    return pd.read_csv(
        get_project_root()
        / "src"
        / "data"
        / "population_insight"
        / "202504_202509_연령별인구현황_월간 - 최종.csv",
        index_col=0,
    )


def get_move_people2025(): 
    return pd.read_excel(
        get_project_root()
        / "src"
        / "data"
        / "population_insight"
        / "인구이동_전출입_2025년_1~8월_합산.xlsx"
    )

def get_move_people2024():
    return pd.read_excel(
        get_project_root()
        / "src"
        / "data"
        / "population_insight"
        / "인구이동_전출입_2024년(연간) - 최종.xlsx"
    )


"""
아래의 pag_pg 는 컨테이너 명입니다.
아래의 ragdb는 데이터베이스명 입니다.

docker cp ./age_population.sql rag_pg:/tmp/age_population.sql
docker exec -it rag_pg psql -U postgres -d ragdb -f /tmp/age_population.sql

CREATE TABLE tmp_migration (
    "전출지" TEXT,
    "전입지" TEXT,
    "계" INT
);

COPY tmp_migration("전출지", "전입지", "계")
FROM '/tmp/move_2024.csv'
DELIMITER ','
CSV HEADER;

CREATE TABLE age_population (
    id SERIAL PRIMARY KEY,
    year INT,
    origin TEXT,
    destination TEXT,
    total INT
);

INSERT INTO age_population (year, origin, destination, total)
SELECT 2024, "전출지", "전입지", "계" FROM tmp_migration;

DROP TABLE tmp_migration;
select count(*) from age_population;
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm import LLMProfile

system_prompt = """
당신은 TextToSQL 을 전문으로 맞을 LLM 입니다.

[스키마 설명]
테이블명: age_population
사용 DB: PostgresSQL
설명: 
  - 대한민국 지역 간 인구 이동 통계 데이터를 저장한 테이블입니다.
  - 전출지 혹은 전입지가 서울 및 서울의 자치구 지역만 모아놓은 데이터 입니다. 
  - 각 행(row)은 특정 연도(`year`)에 한 지역(`origin`)에서 다른 지역(`destination`)으로 이동한 인구 수(`total`)를 나타냅니다.
  - year가 2025 일 경우 해당 데이터는 1~8월 합쳐서 total을 만든것입니다.
  - year가 2024 일 경우 해당 데이터는 1~12월을 합쳐서 total을 만든것입니다.

컬럼 구조:
  - id: 정수형, 기본 키 (각 행의 고유 식별자)
  - year: 정수형, 데이터의 기준 연도 (예: 2024)
  - origin: 텍스트, 전출지 (예: "전국", "서울 영등포구")
  - destination: 텍스트, 전입지 (예: "서울", "서울 종로구")
  - total: 정수형, 해당 이동 인원 수 (단위: 명)

데이터 예시:
  | id | year | origin | destination | total  |
  |----|------|---------|-------------|-------|
  | 1  | 2024 | 전국    | 서울        | 893566 |
  | 2  | 2024 | 전국    | 서울 종로구 | 14483   |
  | 3  | 2024 | 전국    | 서울 중구   | 14333   |

주의사항:
  - `origin`과 `destination`은 모두 문자열이며, 시·도 또는 자치구 단위 명칭이 들어갑니다.
  - `total`은 특정 지역 쌍(origin → destination) 간의 이동 인원 총합을 나타냅니다.
  - 연도(`year`)별로 동일한 origin–destination 쌍이 존재할 수 있습니다.

[출력 형식]
- 사용자 질문에 맞는 PostgresSQL 쿼리문을 만들어주십시오
- 사용자 질문이 위 스키마 범위를 벗어나면 스키마에서 가능한 선까지만 쿼리를 생성하시오.

[필수 SELECT 컬럼 규칙]
- SELECT 절에는 반드시 year, origin, destination, total 4개 컬럼만 포함하세요.
- id 컬럼은 절대 SELECT에 포함하지 마세요.
- SELECT * 를 사용하지 마세요.
- 컬럼 alias(AS)를 사용하지 마세요. 반드시 원본 컬럼명 그대로 사용하세요.
- 올바른 예: SELECT year, origin, destination, total FROM age_population WHERE ...
- 잘못된 예: SELECT * FROM age_population / SELECT year AS "연도" ...
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm import LLMProfile
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os 

def get_move_population(question: str):
    """인구 이동 통계를 PostgreSQL에서 조회합니다.

    [동작 흐름]
    1단계: LLM이 사용자 주소를 "서울 자치구" 형식으로 정규화
    2단계: LLM이 정규화된 주소로 SQL 생성 (StructuredOutput으로 컬럼 고정)
    3단계: SQL 실행 → list[dict] 반환

    [StructuredOutput 적용 이유]
    이전에 StrOutputParser()로 자유 텍스트 SQL을 받았을 때 LLM이
    SELECT *, 한글 alias 등 변형 SQL을 생성하여 하류 move_population_to_drive()에서
    KeyError("['origin', 'destination', 'total'] not in index") 발생.
    MovePopulationQuery 스키마로 SELECT 컬럼을 year, origin, destination, total로 강제.
    """
    load_dotenv()

    # 1단계: 주소 정규화 (예: "서울특별시 송파구 석촌동" → "서울 송파구")
    gen_query_llm = LLMProfile.dev_llm().invoke(
        f"""
        당신은 질문을 맞춤으로 생성을 담당한 역할입니다. 주소를 입력으로 받습니다.
        해당 주소의 주소 내용을 쿼리용으로 가공할 예정입니다. 예시는 아래와 같습니다.

        [예시]
        1. "서울특별시 종로구" -> "서울 종로구"
        2. "서울 강동구 서초동" -> "서울 강남구"
        3. "서울특별시 송파구 석촌동" -> "서울 송파구"

        [강력 지침]
        - xxx구 까지만 얘기하세요
        - 자치구 말이외에 절대 다른말을 하지마세요
        - 자치구만 말씀하세요
        - xx동은 절대 말하지마세요

        질문: {question}
        """
    )
    print(gen_query_llm.content)
    new_question = gen_query_llm.content

    # 2단계: SQL 생성 (StructuredOutput으로 컬럼 고정)
    from agents.state.structured_schemas import MovePopulationQuery

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{question}")
    ])

    llm = LLMProfile.dev_llm().with_structured_output(MovePopulationQuery)
    response = llm.invoke(prompt.format_messages(question=new_question))
    query = response.sql

    # 3단계: SQL 실행
    connection_url = os.getenv("POSTGRES_URL")
    engine = create_engine(connection_url)

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(row._mapping) for row in result.fetchall()]

    return rows