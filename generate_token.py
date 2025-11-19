import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]

def generate_token():
    project_root = Path(__file__).parent
    credentials_path = project_root / "credentials.json"
    token_path = project_root / "token.json"
    
    if not credentials_path.exists():
        print(f"❌ credentials.json 파일을 찾을 수 없습니다: {credentials_path}")
        print("프로젝트 루트에 credentials.json 파일을 배치해주세요.")
        return
    
    creds = None
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        print("✅ 기존 token.json 파일을 찾았습니다.")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("♻️  토큰이 만료되어 갱신 중...")
            creds.refresh(Request())
        else:
            print("🌐 Google OAuth 인증을 시작합니다...")
            print("브라우저 창이 열리면 Google 계정으로 로그인하고 권한을 승인해주세요.")
            
            with open(credentials_path, "r") as f:
                credentials_config = json.load(f)
            
            flow = InstalledAppFlow.from_client_config(credentials_config, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        print(f"✅ token.json 파일이 생성되었습니다: {token_path}")
        print("\n📋 Railway 환경변수 설정 방법:")
        print("1. 생성된 token.json 파일을 열어서 전체 내용을 복사하세요")
        print("2. Railway Variables에 다음을 추가하세요:")
        print("   변수명: GOOGLE_TOKEN_JSON")
        print("   값: token.json 파일의 전체 내용 (JSON 형식)")
    else:
        print("✅ token.json이 유효합니다.")
        print(f"파일 위치: {token_path}")
        print("\n📋 Railway 환경변수 설정을 위해 token.json 내용을 복사하세요:")

if __name__ == "__main__":
    generate_token()

