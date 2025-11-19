import io
import os
import pandas as pd
from typing import Union, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from utils.util import get_project_root

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_drive_service(
    credentials_json: str = get_project_root() / "credentials.json",
    token_json: str = get_project_root() / "token.json",
):
    """OAuth 인증 → Drive 서비스 객체 반환"""
    creds = None
    if os.path.exists(token_json):
        creds = Credentials.from_authorized_user_file(token_json, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_json, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_json, "w") as token:
            token.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def upload_to_drive(
    data: Union[str, bytes, pd.DataFrame, io.BytesIO],
    filename: str,
    folder_id: Optional[str] = None,
    mime_type: str = "text/csv",
) -> str:
    """
    📤 Google Drive 업로드 및 공개 링크 생성
    - data: 문자열 경로, 바이트, DataFrame, BytesIO 지원
    - filename: Google Drive에 저장할 이름
    - folder_id: (선택) 업로드할 폴더 ID
    - 반환값: 공개 다운로드 링크
    """
    service = _get_drive_service()

    # 파일을 메모리 스트림으로 변환
    if isinstance(data, pd.DataFrame):
        buffer = io.BytesIO()
        data.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
    elif isinstance(data, bytes):
        buffer = io.BytesIO(data)
    elif isinstance(data, str) and os.path.exists(data):
        buffer = open(data, "rb")
    elif isinstance(data, io.BytesIO):
        buffer = data
        buffer.seek(0)
    else:
        raise TypeError(
            "지원하지 않는 data 형식입니다. (DataFrame, bytes, str[경로], BytesIO)"
        )

    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(buffer, mimetype=mime_type)
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = file.get("id")

    # “링크가 있는 사람은 누구나 보기 가능” 권한 추가
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # 다운로드 가능한 링크 생성
    download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    return download_url
