import os
import json
import base64
import markdown
import weasyprint
from pathlib import Path
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from utils.util import get_project_root


# -------------------------------------------------
# Gmail 인증
# -------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]
BASE_DIR = get_project_root()
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")


def gmail_authenticate():
    creds = None

    token_json_str = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json_str:
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        print("환경변수에서 토큰 로드 완료")
    elif os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("Gmail token 갱신 완료")
            if token_json_str:
                print("경고: 환경변수 토큰은 갱신 후 파일로 저장되지 않습니다.")
            else:
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
                    print(f"토큰 저장 완료: {TOKEN_PATH}")
        else:
            is_docker = (
                os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
            )
            if is_docker:
                raise RuntimeError(
                    "Docker 환경에서는 브라우저 인증이 불가능합니다. "
                    "GOOGLE_TOKEN_JSON 환경변수에 인증된 토큰을 설정해주세요."
                )

            print("최초 인증 중... (브라우저 창 열림)")

            credentials_config = None
            if os.getenv("GOOGLE_CREDENTIALS_JSON"):
                credentials_config = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
            elif os.path.exists(CREDENTIALS_PATH):
                with open(CREDENTIALS_PATH, "r") as f:
                    credentials_config = json.load(f)
            else:
                raise FileNotFoundError(
                    "credentials.json 파일 또는 GOOGLE_CREDENTIALS_JSON 환경 변수가 필요합니다."
                )

            flow = InstalledAppFlow.from_client_config(credentials_config, SCOPES)
            creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
                print(f"토큰 저장 완료: {TOKEN_PATH}")

    return creds


def _ensure_blank_line_before_tables(md: str) -> str:
    """
    마크다운 표(| ... | 패턴)가 일반 텍스트 바로 뒤에 오면
    python-markdown이 표를 인식하지 못하므로, 빈 줄을 강제 삽입한다.

    python-markdown의 tables 확장은 블록 단위로 파싱하는데,
    빈 줄 없이 텍스트에 이어진 표는 텍스트와 같은 블록으로 묶여
    <table> 대신 <p> 태그로 변환되어 | 기호가 그대로 노출된다.

    이 함수가 없으면: "표) 제목\n| 헤더 |..." → <p>표) 제목\n| 헤더 |...</p>
    이 함수가 있으면: "표) 제목\n\n| 헤더 |..." → <p>표) 제목</p><table>...</table>
    """
    lines = md.split("\n")
    result = []
    for line in lines:
        if (
            line.strip().startswith("|")
            and result # 리스트에 뭔가 있을 때만
            and result[-1].strip() != "" # 마지막 요소(이전 줄)가 비어있지 않을 때만
            and not result[-1].strip().startswith("#") # 제목(#) 뒤에는 빈 줄 없어도 표가 정상 인식
            and not result[-1].strip().startswith("|") # 표 다음에는 빈 줄 없어도 표가 정상 인식
        ):
            result.append("") # 빈 문자열(빈 줄) 삽입
        result.append(line)
    return "\n".join(result)


def _strip_outer_fence(md: str) -> str:
    """
    ```...``` 로 전체가 둘러싸여 있으면 그 껍데기만 벗겨줌.
    ```markdown 로 시작해도 잘라줌.
    """
    text = md.strip()

    # 맨 앞 라인
    if text.startswith("```"):
        lines = text.splitlines()
        # 첫 줄은 ``` 또는 ```markdown 같은 거니까 버림
        first = lines[0].strip()
        # 마지막 줄이 ``` 이면 그것도 버림
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    return text


# -------------------------------------------------
# Markdown → PDF 변환 (WeasyPrint 버전)
# -------------------------------------------------
def markdown_to_pdf(md_text: str, filename: str) -> str:
    """
    Markdown을 PDF로 변환해서 output 폴더에 저장 후 경로 반환
    (WeasyPrint 사용, 파일명/메타데이터 고정)
    Docker 환경에서는 임시 파일로 사용되며 Google Drive 업로드 후 삭제됩니다.
    """
    output_dir = get_project_root() / "output"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"경고: output 폴더 생성 실패: {e}")
        output_dir = Path("/tmp")
        print(f"임시 디렉토리 사용: {output_dir}")

    output_path = output_dir / filename

    # PDF 문서 제목(메타데이터)은 파일명에서 확장자만 제거해서 사용
    pdf_title = os.path.splitext(filename)[0]

    try:
        # 표 앞에 빈 줄이 없으면 python-markdown이 <table>로 파싱하지 못함
        md_text = _ensure_blank_line_before_tables(md_text)

        # Markdown → HTML
        html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

        # HTML 템플릿: 문서 <title> 을 반드시 넣어주면 'Unnamed' 메타데이터 방지
        html_template = f"""
        <html>
          <head>
            <meta charset="utf-8"/>
            <title>{pdf_title}</title>
            <style>
              @page {{ size: A4; margin: 20mm; }}
              @font-face {{
                font-family: 'Noto Sans CJK KR';
                src: local('Noto Sans CJK KR');
              }}
              body {{
                font-family: 'Noto Sans CJK KR', 'Noto Sans KR', 'Noto Sans', 'Malgun Gothic', 'Nanum Gothic', Arial, sans-serif;
                line-height: 1.6;
                color: #222;
              }}
              h1, h2, h3, h4 {{ 
                color: #333;
                font-family: 'Noto Sans CJK KR', 'Noto Sans KR', 'Noto Sans', 'Malgun Gothic', 'Nanum Gothic', Arial, sans-serif;
              }}
              table {{
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
                font-family: 'Noto Sans CJK KR', 'Noto Sans KR', 'Noto Sans', 'Malgun Gothic', 'Nanum Gothic', Arial, sans-serif;
              }}
              th, td {{
                border: 1px solid #aaa;
                padding: 6px 10px;
                text-align: left;
              }}
              code {{
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 3px;
              }}
            </style>
          </head>
          <body>{html}</body>
        </html>
        """

        # 핵심 1) base_url 지정 (상대자원/경로 안정화)
        html_obj = weasyprint.HTML(string=html_template, base_url=str(output_dir))

        # 핵심 2) 파일 핸들로 직접 쓰기 (경로/문자 인코딩 이슈 회피, 파일명 고정)
        with open(output_path, "wb") as fp:
            # 필요하면 stylesheets=[weasyprint.CSS(string="...")] 추가 가능
            html_obj.write_pdf(fp, presentational_hints=True)

        print(f"PDF 생성 완료: {output_path}")
    except Exception as e:
        print(f"PDF 변환 실패: {e}")

    return str(output_path)


# def markdown_to_pdf(md_text: str, filename: str) -> str:
#     """
#     Markdown을 PDF로 변환해서 output 폴더에 저장 후 경로 반환
#     (Pandoc/XeLaTeX 없이 동작. 협업용 간소 버전)
#     """
#     output_dir = get_project_root() / "output"
#     os.makedirs(output_dir, exist_ok=True)
#     output_path = output_dir / filename

#     try:
#         # Markdown → HTML
#         html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

#         # 기본 스타일 추가 (한글 폰트 포함)
#         html_template = f"""
#         <html>
#           <head>
#             <meta charset="utf-8"/>
#             <style>
#               body {{
#                 font-family: 'Noto Sans KR', 'Malgun Gothic', Arial, sans-serif;
#                 line-height: 1.6;
#                 color: #222;
#                 margin: 40px;
#               }}
#               h1, h2, h3, h4 {{ color: #333; }}
#               table {{
#                 border-collapse: collapse;
#                 width: 100%;
#                 margin-top: 10px;
#                 margin-bottom: 10px;
#               }}
#               th, td {{
#                 border: 1px solid #aaa;
#                 padding: 6px 10px;
#                 text-align: left;
#               }}
#               code {{
#                 background-color: #f5f5f5;
#                 padding: 2px 4px;
#                 border-radius: 3px;
#               }}
#             </style>
#           </head>
#           <body>{html}</body>
#         </html>
#         """

#         # HTML → PDF 변환
#         weasyprint.HTML(string=html_template).write_pdf(str(output_path))
#         print(f"📄 PDF 생성 완료: {output_path}")
#     except Exception as e:
#         print(f"❌ PDF 변환 실패: {e}")
#     return str(output_path)


from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build


def upload_to_drive(file_path: str, folder_id: str | None = None) -> str:
    """
    PDF 파일을 Google Drive에 업로드하고, 누구나 열람 가능한 링크를 리턴한다.
    """
    # Gmail이 아니라 Drive 서비스 따로!
    creds = gmail_authenticate()
    drive_service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(file_path, mimetype="application/pdf")

    uploaded = (
        drive_service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink, webContentLink",
        )
        .execute()
    )

    file_id = uploaded["id"]

    # 링크 가진 사람은 보기 가능하게
    drive_service.permissions().create(
        fileId=file_id, body={"type": "anyone", "role": "reader"}
    ).execute()

    return uploaded["webViewLink"]


def send_gmail(
    to: str,
    title: str,
    md_content_final: str,
    md_content_source: str,
    drive_links: dict[str, str] | None = None,
):
    creds = gmail_authenticate()
    service = build("gmail", "v1", credentials=creds)

    # Markdown → PDF 변환
    final_pdf_path = markdown_to_pdf(
        _strip_outer_fence(md_content_final), f"{title}_최종보고서.pdf"
    )
    source_pdf_path = markdown_to_pdf(
        _strip_outer_fence(md_content_source), f"{title}__데이터출처모음.pdf"
    )

    # PDF를 Google Drive에 업로드
    final_link = upload_to_drive(final_pdf_path)
    source_link = upload_to_drive(source_pdf_path)

    # Docker 환경에서 임시 파일 정리 (디스크 공간 절약)
    try:
        if os.path.exists(final_pdf_path):
            os.remove(final_pdf_path)
            print(f"임시 파일 삭제: {final_pdf_path}")
        if os.path.exists(source_pdf_path):
            os.remove(source_pdf_path)
            print(f"임시 파일 삭제: {source_pdf_path}")
    except Exception as e:
        print(f"임시 파일 삭제 실패 (무시): {e}")

    # Google Drive 링크 HTML 섹션 구성
    drive_links_html = ""
    if drive_links:
        drive_links_html = "<hr/><h4>데이터 다운로드 링크</h4><ul>"
        for name, link in drive_links.items():
            drive_links_html += f'<li><a href="{link}" target="_blank">{name}</a></li>'
        drive_links_html += "</ul>"

    # HTML 본문 구성 (클릭하면 Drive 열림)
    html_body = f"""
    <html>
      <body style="font-family:'Noto Sans KR',Arial,sans-serif;line-height:1.6;color:#222;">
        <h2>{title}</h2>
        <p>
          내부 분석 보고서가 완료되었습니다.<br/>
          아래 링크를 통해 PDF 파일을 다운로드할 수 있습니다.
        </p>

        <ul>
          <li><a href="{final_link}" target="_blank">최종보고서.pdf</a></li>
          <li><a href="{source_link}" target="_blank">데이터출처모음.pdf</a></li>
        </ul>
        <hr/>
        {drive_links_html}
        <hr/>
        <p style="font-size:13px;color:#777;">
          ※ 본 보고서는 내부 검토용입니다.<br/>
          부동산 마케팅 협회 자동화 리포트 시스템 (RAG_COMMANDER)
        </p>
      </body>
    </html>
    """

    # Gmail 본문만 전송 (첨부 제외)
    message = MIMEText(html_body, "html", "utf-8")
    message["to"] = to  # 이게 없어서 400 났던 것
    message["subject"] = title

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=body).execute()
    print(f"메일 전송 완료: {to} (ID: {sent['id']})")
