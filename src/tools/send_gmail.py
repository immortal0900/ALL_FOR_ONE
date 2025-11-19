import os
import base64
import markdown
import weasyprint  # ✅ 추가
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

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print("♻️  Gmail token 갱신 완료")
        else:
            print("🌐 최초 인증 중... (브라우저 창 열림)")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
            print(f"💾 토큰 저장 완료 → {TOKEN_PATH}")

    return creds


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
    """
    output_dir = get_project_root() / "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = output_dir / filename

    # PDF 문서 제목(메타데이터)은 파일명에서 확장자만 제거해서 사용
    pdf_title = os.path.splitext(filename)[0]

    try:
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
              body {{
                font-family: 'Noto Sans KR', 'Malgun Gothic', Arial, sans-serif;
                line-height: 1.6;
                color: #222;
              }}
              h1, h2, h3, h4 {{ color: #333; }}
              table {{
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
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

        print(f"📄 PDF 생성 완료: {output_path}")
    except Exception as e:
        print(f"❌ PDF 변환 실패: {e}")

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

    # ✅ Markdown → PDF 변환
    final_pdf_path = markdown_to_pdf(
        _strip_outer_fence(md_content_final), f"{title}_최종보고서.pdf"
    )
    source_pdf_path = markdown_to_pdf(
        _strip_outer_fence(md_content_source), f"{title}__데이터출처모음.pdf"
    )

    # ✅ PDF를 Google Drive에 업로드
    final_link = upload_to_drive(final_pdf_path)
    source_link = upload_to_drive(source_pdf_path)

    # 🔗 Google Drive 링크 HTML 섹션 구성
    drive_links_html = ""
    if drive_links:
        drive_links_html = "<hr/><h4>📂 데이터 다운로드 링크</h4><ul>"
        for name, link in drive_links.items():
            drive_links_html += f'<li><a href="{link}" target="_blank">{name}</a></li>'
        drive_links_html += "</ul>"

    # ✅ HTML 본문 구성 (클릭하면 Drive 열림)
    html_body = f"""
    <html>
      <body style="font-family:'Noto Sans KR',Arial,sans-serif;line-height:1.6;color:#222;">
        <h2>📑 {title}</h2>
        <p>
          내부 분석 보고서가 완료되었습니다.<br/>
          아래 링크를 통해 PDF 파일을 다운로드할 수 있습니다.
        </p>

        <ul>
          <li>📘 <a href="{final_link}" target="_blank">최종보고서.pdf</a></li>
          <li>📗 <a href="{source_link}" target="_blank">데이터출처모음.pdf</a></li>
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

    # ✅ Gmail 본문만 전송 (첨부 제외)
    message = MIMEText(html_body, "html", "utf-8")
    message["to"] = to  # ⬅︎ 이게 없어서 400 났던 것
    message["subject"] = title

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=body).execute()
    print(f"✅ 메일 전송 완료 → {to} (ID: {sent['id']})")
