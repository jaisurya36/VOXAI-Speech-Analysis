import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.models.database import init_db
from app.api.health import router as health_router
from app.api.media import router as media_router
from app.api.transcription import router as transcription_router
from app.api.content_ai import router as content_ai_router
from app.api.reference import router as reference_router
from app.api.alignment import router as alignment_router
from app.api.features import router as features_router
from app.api.comparison import router as comparison_router
from app.api.flaws import router as flaws_router
from app.api.explanations import router as explanations_router
from app.api.scoring import router as scoring_router
from app.api.dashboard import router as dashboard_router
from app.api.demo import router as demo_router
from app.api.pipeline import router as pipeline_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    # Ensure storage directories exist
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.dirname(backend_dir)
    for dir_path in [settings.upload_dir, settings.generated_dir]:
        if not os.path.isabs(dir_path):
            dir_path = os.path.join(backend_root, dir_path.lstrip('./'))
        os.makedirs(dir_path, exist_ok=True)
    print('Storage directories ready.')
    yield
    # Shutdown
    print('Shutting down...')


app = FastAPI(
    title='Counterpointing Speech Analytics API',
    description='AI-powered objective speech evaluation system',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Dev: allow all; restrict in production
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health_router, prefix='/api')
app.include_router(media_router, prefix='/api')
app.include_router(transcription_router, prefix='/api')
app.include_router(content_ai_router, prefix='/api')
app.include_router(reference_router, prefix='/api')
app.include_router(alignment_router, prefix='/api')
app.include_router(features_router, prefix='/api')
app.include_router(comparison_router, prefix='/api')
app.include_router(flaws_router, prefix='/api')
app.include_router(explanations_router, prefix='/api')
app.include_router(scoring_router, prefix='/api')
app.include_router(dashboard_router, prefix='/api')
app.include_router(demo_router, prefix='/api')
app.include_router(pipeline_router, prefix='/api')


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={'detail': f'Internal server error: {str(exc)}'}
    )


@app.get('/')
async def root():
    return {
        'message': 'Counterpointing Speech Analytics API',
        'docs': '/docs',
        'health': '/api/health'
    }
