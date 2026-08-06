"""FastAPI app for Doc Center file topic routing."""

from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .classifier import DEFAULT_TAU, TopicClassifier
from .extract import extract_text, is_allowed_filename
from .store import FileStore, TokenContribution

classifier: TopicClassifier | None = None
store = FileStore()

_config_lock = Lock()
_current_tau = DEFAULT_TAU


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


class TauUpdate(BaseModel):
    tau: float = Field(..., ge=0.05, le=0.95)


class RouteResponse(BaseModel):
    id: str
    topic: str
    topic_label: str
    status: str
    message: str
    confidence: float
    filename: str
    routed_at: str
    tau: float
    decision_source: str
    contributions: list[dict[str, float | str]]


def _require_classifier() -> TopicClassifier:
    if classifier is None:
        raise HTTPException(status_code=503, detail="Classifier is not loaded.")
    return classifier


def _get_tau() -> float:
    with _config_lock:
        return _current_tau


def _set_tau(tau: float) -> float:
    global _current_tau
    with _config_lock:
        _current_tau = float(tau)
        return _current_tau


def _contrib_dicts(prediction_contributions) -> list[dict[str, float | str]]:
    return [
        {
            "token": c.token,
            "tfidf": round(c.tfidf, 6),
            "coef": round(c.coef, 6),
            "contribution": round(c.contribution, 6),
        }
        for c in prediction_contributions
    ]


def _route_text(article_text: str, filename: str) -> RouteResponse:
    clf = _require_classifier()
    tau = _get_tau()
    try:
        prediction = clf.predict(article_text, tau=tau)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store_contribs = [
        TokenContribution(
            token=c.token,
            tfidf=c.tfidf,
            coef=c.coef,
            contribution=c.contribution,
        )
        for c in prediction.contributions
    ]
    entry = store.add(
        filename=filename,
        topic=prediction.topic,
        topic_label=prediction.topic_label,
        status=prediction.status,
        confidence=prediction.confidence,
        article_text=article_text,
        contributions=store_contribs,
        decision_source="auto",
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
        tau=tau,
        decision_source=entry.decision_source,
        contributions=_contrib_dicts(prediction.contributions),
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    loaded = classifier is not None
    return {
        "status": "ok" if loaded else "degraded",
        "model_loaded": loaded,
        "model_path": str(classifier.model_path) if classifier else None,
        "tau": _get_tau(),
        "default_tau": DEFAULT_TAU,
    }


@app.get("/api/config")
def get_config() -> dict[str, float]:
    return {"tau": _get_tau(), "default_tau": DEFAULT_TAU}


@app.put("/api/config/tau")
def update_tau(body: TauUpdate) -> dict[str, float]:
    return {"tau": _set_tau(body.tau), "default_tau": DEFAULT_TAU}


@app.get("/api/files")
def list_files() -> dict[str, list[dict]]:
    return store.list_all()


@app.get("/api/files/{file_id}")
def get_file(file_id: str) -> dict:
    entry = store.get(file_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return entry.to_detail()


@app.post("/api/files/{file_id}/accept")
def accept_file(file_id: str) -> dict:
    try:
        entry = store.move(
            file_id,
            new_status="accepted",
            decision_source="reviewer:accept",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return entry.to_detail()


@app.post("/api/files/{file_id}/reject")
def reject_file(file_id: str) -> dict:
    try:
        entry = store.move(
            file_id,
            new_status="quarantined",
            decision_source="reviewer:reject",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return entry.to_detail()


@app.post("/api/route", response_model=RouteResponse)
async def route_article(
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> RouteResponse:
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
    return _route_text(body.text.strip(), "pasted-article.txt")
