import streamlit as st
import requests
import os
import urllib3
import ssl
import time
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
    api_url = "https://allforone-production.up.railway.app"

    # SSL 문제 해결을 위한 세션 설정
    session = requests.Session()
    adapter = SSLAdapter(max_retries=3)
    session.mount("https://", adapter)

    try:
        # 1. 작업 시작
        st.info("작업을 시작합니다...")
        start_response = session.post(
            f"{api_url}/invoke",
            json=payload,
            timeout=30,
            verify=False,
        )

        if start_response.status_code != 200:
            st.error(f"작업 시작 실패: {start_response.status_code}")
            st.text(start_response.text)
            st.stop()

        job_data = start_response.json()
        job_id = job_data.get("job_id")

        if not job_id:
            st.error("작업 ID를 받지 못했습니다.")
            st.json(job_data)
            st.stop()

        st.success(f"작업이 시작되었습니다. 작업 ID: {job_id}")

        # 2. 상태 확인 및 폴링
        status_placeholder = st.empty()
        progress_placeholder = st.empty()

        max_wait_time = 1800  # 최대 30분 대기
        check_interval = 5  # 5초마다 확인
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            status_response = session.get(
                f"{api_url}/status/{job_id}",
                timeout=10,
                verify=False,
            )

            if status_response.status_code != 200:
                status_placeholder.error(
                    f"상태 확인 실패: {status_response.status_code}"
                )
                st.text(status_response.text)
                st.stop()

            status_data = status_response.json()
            current_status = status_data.get("status")
            message = status_data.get("message", "")

            if current_status == "completed":
                status_placeholder.success("작업이 완료되었습니다!")
                break
            elif current_status == "failed":
                status_placeholder.error(f"작업이 실패했습니다: {message}")
                st.stop()
            elif current_status == "running":
                status_placeholder.info(f"작업 실행 중... ({elapsed_time}초 경과)")
                progress_placeholder.progress(min(elapsed_time / max_wait_time, 0.95))
            elif current_status == "pending":
                status_placeholder.info(f"작업 대기 중... ({elapsed_time}초 경과)")

            time.sleep(check_interval)
            elapsed_time += check_interval

        if elapsed_time >= max_wait_time:
            st.error("작업이 시간 내에 완료되지 않았습니다. 나중에 다시 확인해주세요.")
            st.info(f"작업 ID: {job_id}")
            st.stop()

        # 3. 결과 조회
        st.info("결과를 가져오는 중...")
        result_response = session.get(
            f"{api_url}/result/{job_id}",
            timeout=30,
            verify=False,
        )

        if result_response.status_code == 200:
            data = result_response.json()
            st.success("보고서 생성 완료!")
            st.json(data)
        elif result_response.status_code == 202:
            st.warning("작업이 아직 완료되지 않았습니다. 잠시 후 다시 시도해주세요.")
            st.text(result_response.text)
        else:
            st.error(f"결과 조회 실패: {result_response.status_code}")
            st.text(result_response.text)

    except requests.exceptions.SSLError as e:
        st.error("SSL 연결 오류가 발생했습니다.")
        st.write("Railway 서버의 SSL 인증서 문제일 수 있습니다.")
        st.write(f"오류 상세: {str(e)}")
    except requests.exceptions.RequestException as e:
        st.error(f"요청 실패: {str(e)}")
    except Exception as e:
        st.error(f"예상치 못한 오류: {str(e)}")
        import traceback

        st.text(traceback.format_exc())
