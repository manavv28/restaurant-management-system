"""Run daily: python -m app.jobs. Deletes personal search traces after 30 days."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from .database import Session, Search, Interaction, Transaction, Redemption
def retain():
    with Session() as db:
        cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
        db.execute(delete(Search).where(Search.created_at < cutoff))
        db.execute(delete(Interaction).where(Interaction.created_at < cutoff))
        audit_cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).isoformat()
        db.execute(delete(Transaction).where(Transaction.created_at < audit_cutoff))
        db.execute(delete(Redemption).where(Redemption.created_at < audit_cutoff))
        db.commit()
if __name__ == '__main__': retain()
