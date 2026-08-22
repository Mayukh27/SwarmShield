"""Explicit CLI for a small, licensed security corpus; never runs at startup."""
from __future__ import annotations
import argparse
from app.db.base import SessionLocal
from app.services.rag_service import ingest_document

_CURATED = {
    "owasp": [("OWASP Top 10 / LLM guidance", "Treat untrusted input as data, apply least privilege, validate tool calls, and retain auditable evidence.", "security_guidance", "OWASP")],
    "cwe": [("CWE-79", "Cross-site scripting: encode output, validate input, use safe templating and content security policy.", "cwe", "CWE")],
    "cve": [], "exploitdb": [],
}

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a curated, locally supplied security corpus")
    parser.add_argument("--source", required=True, choices=sorted(_CURATED))
    parser.add_argument("--limit", type=int, default=1000); parser.add_argument("--since")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        for title, content, doc_type, source in _CURATED[args.source][:args.limit]:
            _, added = ingest_document(db, source=source.lower(), title=title, content=content,
                document_type=doc_type, metadata={"license": "operator supplied/verify before production"}, dry_run=args.dry_run)
            print(f"{'would ingest' if args.dry_run else 'ingested' if added else 'duplicate'}: {title}")
    finally: db.close()

if __name__ == "__main__": main()
