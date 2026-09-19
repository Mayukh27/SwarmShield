"""Curated, local hybrid retrieval. Retrieved text is data, never executable."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.knowledge_document import KnowledgeDocument
from app.services.embedding_service import cosine_similarity, embed


def _hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def _contains_secret(value: str) -> bool:
    return bool(re.search(r"(?i)(api[_ -]?key|password|authorization|session[_ -]?cookie)\s*[:=]", value))


def ingest_document(db: Session, *, source: str, title: str, content: str,
                    document_type: str = "security_guidance", source_id: str | None = None,
                    metadata: dict[str, Any] | None = None, tags: list[str] | None = None,
                    cwe: str | None = None, cve: str | None = None, severity: str | None = None,
                    product: str | None = None, dry_run: bool = False) -> tuple[KnowledgeDocument | None, bool]:
    if not content.strip():
        raise ValueError("Knowledge content is required")
    if _contains_secret(content):
        raise ValueError("Refusing to store possible secret material in security knowledge")
    content_hash = _hash(content)
    existing = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == content_hash).first()
    if existing:
        return existing, False
    if dry_run:
        return None, True
    vector = embed(content)
    document = KnowledgeDocument(source=source, source_id=source_id, title=title[:500], content=content,
        document_type=document_type, metadata_json=metadata or {}, tags=tags or [], cwe=cwe, cve=cve,
        severity=severity, product=product, content_hash=content_hash, embedding=vector,
        embedding_dimension=str(len(vector)))
    db.add(document); db.commit(); db.refresh(document)
    return document, True


def search(db: Session, query: str, *, limit: int = 6, metadata: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Small-dataset metadata + lexical + local-cosine hybrid search."""
    rows = db.query(KnowledgeDocument)
    for field in ("source", "document_type", "cwe", "cve", "product"):
        if metadata and metadata.get(field):
            rows = rows.filter(getattr(KnowledgeDocument, field) == metadata[field])
    query_vector, terms = embed(query), set(re.findall(r"[a-z0-9_+-]{2,}", query.lower()))
    ranked = []
    for doc in rows.all():
        words = set(re.findall(r"[a-z0-9_+-]{2,}", (doc.title + " " + doc.content).lower()))
        lexical = len(terms & words) / max(len(terms), 1)
        semantic = cosine_similarity(query_vector, doc.embedding)
        score = 0.55 * semantic + 0.45 * lexical
        if score > 0:
            ranked.append((score, doc))
    return [{"id": str(d.id), "title": d.title, "content": d.content, "source": d.source,
             "document_type": d.document_type, "cwe": d.cwe, "cve": d.cve, "score": round(score, 4)}
            for score, d in sorted(ranked, key=lambda item: item[0], reverse=True)[:max(0, limit)]]


def assemble_context(results: list[dict[str, Any]], max_chars: int = 12000) -> str:
    chunks, used = [], 0
    for item in results:
        body = item["content"][:2000]
        chunk = f"[{item['source']}] {item['title']}: {body}"
        if used + len(chunk) > max_chars:
            break
        chunks.append(chunk); used += len(chunk)
    return "\n".join(chunks)
