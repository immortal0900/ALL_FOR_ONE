from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional

from agents.main.main_agent import graph_builder
from agents.state.start_state import StartInput

# 그래프 한 번만 컴파일
graph = graph_builder.compile()

# 작업 상태 저장소 (메모리)
jobs: Dict[str, Dict] = {}


class GraphRequest(BaseModel):
    start_input: StartInput


class GraphResponse(BaseModel):
    output: dict


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    message: str
    created_at: str


app = FastAPI(title="Service API")

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # 로컬 개발
        "https://*.streamlit.app",  # Streamlit Cloud
        "https://*.railway.app",  # Railway
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 원본 예외, 스택트레이스 등을 로깅
    import traceback

    tb = traceback.format_exc()
    print(f"Unhandled error: {tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


async def run_graph_task(job_id: str, start_input: dict):
    """백그라운드에서 그래프 실행하는 함수"""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "작업 실행 중..."

        result = await graph.ainvoke({"start_input": start_input})

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "작업 완료"
        jobs[job_id]["result"] = result
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"Error in run_graph_task: {tb}")

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"작업 실패: {str(e)}"
        jobs[job_id]["error"] = str(e)


@app.post("/invoke", response_model=JobResponse)
async def invoke_graph(request: GraphRequest):
    """작업 시작 - 즉시 job_id 반환"""
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "pending",
        "message": "작업 대기 중...",
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }

    # 백그라운드 작업 시작
    asyncio.create_task(run_graph_task(job_id, request.start_input.model_dump()))

    return JobResponse(
        job_id=job_id, status="pending", message="작업이 시작되었습니다."
    )


@app.get("/status/{job_id}", response_model=StatusResponse)
async def get_job_status(job_id: str):
    """작업 상태 확인"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        message=job["message"],
        created_at=job["created_at"],
    )


@app.get("/result/{job_id}", response_model=GraphResponse)
async def get_job_result(job_id: str):
    """작업 결과 조회"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    job = jobs[job_id]

    if job["status"] == "pending" or job["status"] == "running":
        raise HTTPException(
            status_code=202,
            detail=f"작업이 아직 완료되지 않았습니다. 현재 상태: {job['status']}",
        )

    if job["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"작업이 실패했습니다: {job.get('error', '알 수 없는 오류')}",
        )

    if job["status"] == "completed" and job["result"]:
        return GraphResponse(output=job["result"])

    raise HTTPException(status_code=500, detail="결과를 찾을 수 없습니다.")


@app.get("/")
def health_check():
    return {"status": "ok"}
