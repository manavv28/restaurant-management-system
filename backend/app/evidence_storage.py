"""Bounded public-source artifacts; independent of web authentication secrets."""
import hashlib
from sqlalchemy import select,func
from .database import BronzeArtifact


def save_bronze(db,source_id,html):
    digest=hashlib.sha256(html.encode()).hexdigest()
    identifier=hashlib.sha256((str(source_id)+digest).encode()).hexdigest()
    if db.get(BronzeArtifact,identifier):return
    if len(html.encode())>1_000_000:return
    if (db.scalar(select(func.count()).select_from(BronzeArtifact)) or 0)>=50:return
    db.add(BronzeArtifact(id=identifier,source_id=source_id,content_hash=digest,content=html));db.flush()
