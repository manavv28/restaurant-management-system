"""Run daily: python -m app.jobs. Deletes personal search traces after 30 days."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete,select
from .database import Session, Search, Interaction, Transaction, Redemption, AuthSession, SecurityToken, RateLimit, OwnershipProof, ProviderOAuthState, ProviderConnection, BronzeArtifact, AgentRun, ResearchRequest, DealVoucher, now
def retain():
    with Session() as db:
        db.execute(delete(ProviderConnection).where(ProviderConnection.retain_until < now()))
        db.execute(delete(ProviderOAuthState).where(ProviderOAuthState.expires_at < now()))
        db.execute(delete(AuthSession).where(AuthSession.expires_at < now()))
        db.execute(delete(SecurityToken).where(SecurityToken.expires_at < now()))
        db.execute(delete(RateLimit).where(RateLimit.expires_at < now()))
        db.execute(delete(OwnershipProof).where(OwnershipProof.expires_at < now(),OwnershipProof.verified_at.is_(None)))
        db.execute(delete(BronzeArtifact).where(BronzeArtifact.created_at < (datetime.now(timezone.utc)-timedelta(days=7)).isoformat()))
        cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
        db.execute(delete(AgentRun).where(AgentRun.created_at < cutoff))
        db.execute(delete(ResearchRequest).where(ResearchRequest.created_at < cutoff))
        db.execute(delete(Search).where(Search.created_at < cutoff))
        db.execute(delete(Interaction).where(Interaction.created_at < cutoff))
        audit_cutoff=(datetime.now(timezone.utc)-timedelta(days=365)).isoformat()
        db.execute(delete(Transaction).where(Transaction.created_at < audit_cutoff))
        db.execute(delete(DealVoucher).where(DealVoucher.expires_at < audit_cutoff))
        db.execute(delete(Redemption).where(Redemption.created_at < audit_cutoff,Redemption.id.not_in(select(DealVoucher.redemption_id))))
        db.commit()
if __name__ == '__main__': retain()
