import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from threading import RLock
from typing import Dict, Optional


_doc_id_var: ContextVar[Optional[str]] = ContextVar("doc_id", default=None)
_provided_classification_var: ContextVar[str] = ContextVar("provided_classification", default="unknown")
_stage_var: ContextVar[Optional[str]] = ContextVar("stage", default=None)


def _sanitize_filename(value: str) -> str:
    sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.lower().strip())
    return sanitized or "unknown"


class ContextFilter(logging.Filter):
    """Inyecta contexto del documento en cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.doc_id = _doc_id_var.get()
        record.provided_classification = _provided_classification_var.get()
        record.stage = _stage_var.get()
        return True


class ProvidedClassificationFileHandler(logging.Handler):
    """
    Handler que segmenta los logs por provided_classification usando archivos rotativos.
    """

    def __init__(
        self,
        base_dir: str,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handlers: Dict[str, RotatingFileHandler] = {}
        self._lock = RLock()
        os.makedirs(self.base_dir, exist_ok=True)

    def setFormatter(self, fmt: logging.Formatter) -> None:
        super().setFormatter(fmt)
        for handler in self._handlers.values():
            handler.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        classification = getattr(record, "provided_classification", None) or "unknown"
        filename_key = _sanitize_filename(str(classification))

        with self._lock:
            handler = self._handlers.get(filename_key)
            if handler is None:
                file_path = os.path.join(self.base_dir, f"{filename_key}.log")
                handler = RotatingFileHandler(
                    file_path,
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8",
                )
                if self.formatter:
                    handler.setFormatter(self.formatter)
                self._handlers[filename_key] = handler

        handler.emit(record)

    def close(self) -> None:
        with self._lock:
            for handler in self._handlers.values():
                handler.close()
            self._handlers.clear()
        super().close()


def configure_logging() -> None:
    """
    Configura logging global con contexto por documento y segmentación por provided_classification.
    """
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [doc=%(doc_id)s] [provided=%(provided_classification)s] "
        "[stage=%(stage)s] %(name)s - %(message)s"
    )

    context_filter = ContextFilter()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)

    provided_handler = ProvidedClassificationFileHandler(base_dir=os.path.join("logs", "provided"))
    provided_handler.setLevel(logging.INFO)
    provided_handler.setFormatter(formatter)
    provided_handler.addFilter(context_filter)

    logging.basicConfig(level=logging.INFO, handlers=[console_handler, provided_handler])


@contextmanager
def document_logging_context(
    doc_id: Optional[str] = None,
    provided_classification: Optional[str] = None,
    stage: Optional[str] = None,
):
    """
    Context manager para asociar logs con un documento y su clasificación.
    """
    tokens = []
    if doc_id is not None:
        tokens.append((_doc_id_var, _doc_id_var.set(str(doc_id))))
    if provided_classification:
        tokens.append(
            (_provided_classification_var, _provided_classification_var.set(str(provided_classification)))
        )
    else:
        tokens.append((_provided_classification_var, _provided_classification_var.set("unknown")))
    if stage is not None:
        tokens.append((_stage_var, _stage_var.set(stage)))

    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def set_stage(stage: Optional[str]) -> None:
    """Actualiza la etapa actual del procesamiento para el contexto de logging."""
    _stage_var.set(stage)

