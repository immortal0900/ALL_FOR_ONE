# UV 가상환경 동기화 가이드

uv를 사용하여 requirements.txt와 가상환경을 동기화하는 방법입니다.

## 1. 기본 명령어

### requirements.txt에서 설치

```cmd
# 가상환경 활성화 (Windows CMD)
.venv\Scripts\activate.bat

# requirements.txt의 패키지 설치
uv pip install -r requirements.txt
```

### requirements.txt와 정확히 동기화 (권장)

```cmd
# 가상환경 활성화
.venv\Scripts\activate.bat

# requirements.txt에 있는 패키지만 설치하고, 없는 패키지는 제거
uv pip sync requirements.txt
```

**차이점:**
- `uv pip install`: requirements.txt의 패키지를 추가만 함 (기존 패키지 유지)
- `uv pip sync`: requirements.txt와 정확히 일치하도록 동기화 (없는 패키지 제거)

## 2. pyproject.toml과 동기화 (uv 권장 방식)

uv는 pyproject.toml을 주로 사용합니다:

```cmd
# 가상환경 활성화
.venv\Scripts\activate.bat

# pyproject.toml 기반으로 설치
uv pip install -e .

# 또는 uv sync 사용 (가상환경 자동 생성 및 동기화)
uv sync
```

## 3. requirements.txt를 pyproject.toml과 동기화

### requirements.txt → pyproject.toml

```cmd
# requirements.txt를 읽어서 pyproject.toml에 추가
uv pip install -r requirements.txt
uv pip freeze > requirements.txt
```

### pyproject.toml → requirements.txt

```cmd
# pyproject.toml 기반으로 requirements.txt 생성
uv pip install -e .
uv pip freeze > requirements.txt
```

## 4. 완전한 동기화 워크플로우

### 방법 1: requirements.txt 사용

```cmd
# 1. 가상환경 생성 (없는 경우)
uv venv

# 2. 가상환경 활성화
.venv\Scripts\activate.bat

# 3. requirements.txt와 동기화
uv pip sync requirements.txt

# 4. 확인
uv pip list
```

### 방법 2: pyproject.toml 사용 (권장)

```cmd
# 1. 가상환경 생성 및 동기화 (한 번에)
uv sync

# 2. 가상환경 활성화
.venv\Scripts\activate.bat

# 3. 확인
uv pip list
```

## 5. 업데이트 및 업그레이드

### requirements.txt 업데이트

```cmd
# 가상환경 활성화
.venv\Scripts\activate.bat

# requirements.txt의 패키지 업그레이드
uv pip install --upgrade -r requirements.txt

# 또는 동기화
uv pip sync requirements.txt --upgrade
```

### 특정 패키지 업데이트

```cmd
uv pip install --upgrade 패키지명
```

## 6. 현재 설치된 패키지 확인

```cmd
# 가상환경 활성화
.venv\Scripts\activate.bat

# 설치된 패키지 목록
uv pip list

# requirements.txt 형식으로 출력
uv pip freeze

# requirements.txt로 저장
uv pip freeze > requirements.txt
```

## 7. 문제 해결

### 가상환경이 없는 경우

```cmd
# 가상환경 생성
uv venv

# 가상환경 활성화
.venv\Scripts\activate.bat
```

### 패키지 충돌 해결

```cmd
# 가상환경 재생성
rmdir /s /q .venv
uv venv
.venv\Scripts\activate.bat
uv pip sync requirements.txt
```

### uv가 설치되지 않은 경우

```cmd
# Windows에서 uv 설치
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 또는 pip로 설치
pip install uv
```

## 8. 자주 사용하는 명령어 요약

```cmd
# 가상환경 생성
uv venv

# 가상환경 활성화 (Windows CMD)
.venv\Scripts\activate.bat

# requirements.txt와 동기화
uv pip sync requirements.txt

# pyproject.toml과 동기화
uv sync

# 패키지 설치
uv pip install 패키지명

# 패키지 제거
uv pip uninstall 패키지명

# 설치된 패키지 목록
uv pip list

# requirements.txt 생성
uv pip freeze > requirements.txt
```

## 9. 현재 프로젝트 권장 방법

이 프로젝트는 `pyproject.toml`을 사용하므로:

```cmd
# 1. 가상환경 생성 및 동기화
uv sync

# 2. 가상환경 활성화
.venv\Scripts\activate.bat

# 3. 실행
python src/streamlit/web.py
```

또는 requirements.txt를 사용하려면:

```cmd
# 1. 가상환경 생성
uv venv

# 2. 가상환경 활성화
.venv\Scripts\activate.bat

# 3. requirements.txt 동기화
uv pip sync requirements.txt
```

