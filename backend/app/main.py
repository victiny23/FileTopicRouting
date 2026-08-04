"""FastAPI app for Doc Center file topic routing."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .classifier import TopicClassifier
from .extract import extract_text, is_allowed_filename
from .store import FileStore

classifier: TopicClassifier | None = None
store = FileStore()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global classifier
    classifier = TopicClassifier()
    yield


app = FastAPI(title="Doc Center Router", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRouteRequest(BaseModel):
    text: str = Field(..., min_length=1)


class RouteResponse(BaseModel):
    id: str
    topic: str
    topic_label: str
    status: str
    message: str
    confidence: float
    filename: str
    routed_at: str


def _require_classifier() -> TopicClassifier:
    if classifier is None:
        raise HTTPException(status_code=503, detail="Classifier is not loaded.")
    return classifier


def _route_text(article_text: str, filename: str) -> RouteResponse:
    clf = _require_classifier()
    try:
        prediction = clf.predict(article_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    entry = store.add(
        filename=filename,
        topic=prediction.topic,
        topic_label=prediction.topic_label,
        status=prediction.status,
    )
    return RouteResponse(
        id=entry.id,
        topic=prediction.topic,
        topic_label=prediction.topic_label,
        status=prediction.status,
        message=prediction.message,
        confidence=round(prediction.confidence, 4),
        filename=filename,
        routed_at=entry.routed_at,
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    loaded = classifier is not None
    return {
        "status": "ok" if loaded else "degraded",
        "model_loaded": loaded,
        "model_path": str(classifier.model_path) if classifier else None,
    }


@app.get("/api/files")
def list_files() -> dict[str, list[dict]]:
    return store.list_all()


@app.post("/api/route", response_model=RouteResponse)
async def route_article(
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> RouteResponse:
    """
    Route via multipart form: optional file and/or text field.
    Prefer file when present and non-empty; otherwise use pasted text.
    """
    article_text = ""
    filename = "pasted-article.txt"

    if file is not None and file.filename:
        raw = await file.read()
        if raw:
            if not is_allowed_filename(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported file type. Upload a .txt, .md, or .pdf file.",
                )
            try:
                article_text = extract_text(file.filename, raw)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            filename = file.filename

    if not article_text and text and text.strip():
        article_text = text.strip()
        filename = "pasted-article.txt"

    if not article_text:
        raise HTTPException(
            status_code=400,
            detail="Provide a .txt, .md, or .pdf file, or paste article text.",
        )

    return _route_text(article_text, filename)


@app.post("/api/route/text", response_model=RouteResponse)
def route_text_json(body: TextRouteRequest) -> RouteResponse:
    """JSON body alternative for paste-only routing."""
    return _route_text(body.text.strip(), "pasted-article.txt")
