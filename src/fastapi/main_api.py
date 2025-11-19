from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import asyncio

from agents.main.main_agent import graph_builder
from agents.state.start_state import StartInput

# 그래프 한 번만 컴파일
graph = graph_builder.compile()


class GraphRequest(BaseModel):
    start_input: StartInput


class GraphResponse(BaseModel):
    output: dict


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


@app.post("/invoke", response_model=GraphResponse)
async def invoke_graph(request: GraphRequest):
    try:
        result = await asyncio.wait_for(
            graph.ainvoke({"start_input": request.start_input.model_dump()}),
            timeout=1200.0,
        )
        return GraphResponse(output=result)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail="요청 처리 시간이 초과되었습니다. (20분 제한)"
        )
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(f"Error in invoke_graph: {tb}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def health_check():
    return {"status": "ok"}
