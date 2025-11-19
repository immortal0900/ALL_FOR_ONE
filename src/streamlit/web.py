import streamlit as st
import requests
import os
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# SSL 경고 메시지 억제
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# SSL 컨텍스트 생성 (DECRYPTION_FAILED_OR_BAD_RECORD_MAC 에러 해결)
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


st.title("AI 멀티에이전트 분양성 검토 솔루션")
st.write("분양성 및 분양가를 판단할 사업지의 정보들을 삽입해보세요!")

# --- 입력 폼 ---
with st.form("report_form"):
    target_area = st.text_input(
        "사업지 장소", placeholder="예: 서울특별시 송파구 신천동"
    )
    main_type = st.text_input("단지 타입", placeholder="예: 84제곱미터")
    total_units = st.text_input("세대수", placeholder="예: 2275")
    email = st.text_input("이메일 주소", placeholder="예: example@gmail.com")

    policy_count = st.number_input(
        "정책 개수(옵션)", min_value=1, max_value=10, value=2, step=1
    )
    policy_options = ["2025.10.15", "2025.06.27", "2025.09.07"]
    policy_selected = st.multiselect(
        "정책 선택", options=policy_options, default=policy_options[:2]
    )
    policy_list_str = str(policy_selected) if policy_selected else None
    brand = st.text_input("브랜드명", placeholder="예: 래미안아이파크")

    submitted = st.form_submit_button("보고서 작성 시작")


if submitted:
    payload = {
        "start_input": {
            "target_area": target_area,
            "main_type": main_type,
            "total_units": f"{total_units}세대" if total_units else "",
            "email": email,
            "policy_count": policy_count,
            "policy_list": policy_list_str or None,
            "brand": brand or None,
        }
    }

    st.write("요청 데이터 미리보기:")
    st.json(payload)

    # --- 요청 ---
    with st.spinner("보고서를 생성 중입니다... 잠시만 기다려주세요. (13 ~ 15분소요)"):

        api_url = "https://allforone-production.up.railway.app"

        # 디버깅: 사용 중인 API URL 표시
        st.write(f"연결 URL: {api_url}")

        try:
            # SSL 문제 해결을 위한 세션 설정
            session = requests.Session()
            adapter = SSLAdapter(max_retries=3)
            session.mount("https://", adapter)

            response = session.post(
                f"{api_url}/invoke",
                json=payload,
                timeout=1200,  # 20 minutes timeout for long report generation
                verify=False,  # SSL 검증 비활성화 (Railway SSL 인증서 문제로 인한 임시 조치)
            )
            if response.status_code == 200:
                data = response.json()
                st.success("보고서 생성 완료!")
            else:
                st.error(f"서버 오류: {response.status_code}")
                st.text(response.text)
        except requests.exceptions.SSLError as e:
            st.error("SSL 연결 오류가 발생했습니다.")
            st.write("Railway 서버의 SSL 인증서 문제일 수 있습니다.")
            st.write(f"오류 상세: {str(e)}")
        except requests.exceptions.RequestException as e:
            st.error(f"요청 실패: {str(e)}")
