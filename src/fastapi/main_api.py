from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import asyncio
import uuid
import traceback
import logging
from datetime import datetime
from typing import Dict, Optional

from agents.main.main_agent import graph_builder
from agents.state.start_state import StartInput

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# 작업 저장소 설정
# -----------------------------------------------------------------------
# 완료/실패 작업은 JOB_TTL_SECONDS 후 자동 삭제되어 메모리 누수를 방지합니다.
# 이 값이 없으면 jobs 딕셔너리가 무한히 커져 서버 OOM이 발생합니다.
# -----------------------------------------------------------------------
JOB_TTL_SECONDS = 1800  # 30분

# 그래프 한 번만 컴파일
graph = graph_builder.compile()

# 작업 상태 저장소 (메모리)
jobs: Dict[str, Dict] = {}


async def _schedule_job_cleanup(job_id: str, delay_seconds: int) -> None:
    """지정된 시간 후 작업 데이터를 메모리에서 삭제합니다.

    Args:
        job_id: 삭제할 작업 ID
        delay_seconds: 삭제까지 대기 시간 (초)
    """
    await asyncio.sleep(delay_seconds)
    removed = jobs.pop(job_id, None)
    if removed:
        logger.info("Job %s cleaned up after %ds TTL", job_id, delay_seconds)


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
    tb = traceback.format_exc()
    logger.error("Unhandled error: %s", tb)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


async def run_graph_task(job_id: str, start_input: dict):
    """백그라운드에서 그래프 실행하는 함수"""
    from utils.langfuse_tracker import tracker
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["message"] = "작업 실행 중..."

        # Langfuse Session ID를 job_id로 주입하여 1회 파이프라인 전체를 단일 Session으로 묶음
        config = tracker.get_langfuse_config(session_id=job_id)
        
        # 외부 통신(도구)들의 관찰 내역까지 모두 포괄하기 위해 session_context 사용
        async with tracker.session_context(session_id=job_id):
            result = await graph.ainvoke({"start_input": start_input}, config=config)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "작업 완료"
        jobs[job_id]["result"] = result
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Error in run_graph_task: %s", tb)

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"작업 실패: {str(e)}"
        jobs[job_id]["error"] = str(e)

    finally:
        # 작업 완료/실패 후 TTL 기반 자동 정리 예약
        asyncio.create_task(_schedule_job_cleanup(job_id, JOB_TTL_SECONDS))


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

    if job["status"] in ("pending", "running"):
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

