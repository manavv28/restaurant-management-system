"""Monthly tiers and deduplicated query eligibility; financial facts stay gateway-verified."""
from datetime import datetime,timedelta,timezone
import json
from sqlalchemy import select,func,or_,and_
from .database import Search,Transaction,Redemption,Campaign,CampaignPolicy,DealVoucher,now
TIERS=['Bronze','Silver','Gold','Platinum']

def meaningful_queries(db,user_id,cuisine=''):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
    rows=db.scalars(select(Search).where(Search.user_id==user_id,Search.created_at>=cutoff,Search.query!='').order_by(Search.created_at,Search.id)).all()
    last={};count=0;total=0
    for row in rows:
        try:
            trace=json.loads(row.trace or '[]')
            if isinstance(trace,list) and any(isinstance(step,dict) and step.get('tool')=='request_clarification' for step in trace):continue
        except (ValueError,TypeError):continue
        key=(row.dish or row.cuisine or '').casefold().strip()
        if not key:continue
        known={'hakka noodles','noodles','biryani','pizza','dosa','sushi','burger','pasta','tacos','paneer tikka','vada pav'}
        if row.results<=0 and (row.cuisine or '').casefold() not in {'chinese','indian','italian','japanese','mexican','south indian'} and (row.dish or '').casefold() not in known:continue
        try:at=datetime.fromisoformat(row.created_at)
        except ValueError:continue
        if key in last and at-last[key]<timedelta(hours=24):continue
        last[key]=at;total+=1
        if not cuisine or (row.cuisine or '').casefold()==cuisine.casefold():count+=1
        if total>=100:break
    return count

def tier_state(db,user_id):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
    tx=db.scalars(select(Transaction).where(Transaction.user_id==user_id,Transaction.created_at>=cutoff,Transaction.simulated.is_(False),Transaction.test_mode.is_(False),Transaction.disputed.is_(False))).all()
    sandbox=db.scalars(select(Transaction).where(Transaction.user_id==user_id,Transaction.created_at>=cutoff,Transaction.test_mode.is_(True),Transaction.disputed.is_(False))).all()
    sandbox_spend=sum(max(0,t.amount_paise-t.refunded_paise) for t in sandbox)
    spend=sum(max(0,t.amount_paise-t.refunded_paise) for t in tx)
    queries=meaningful_queries(db,user_id)
    points=queries*10+spend//1000
    thresholds=[0,50,200,500];level=max(i for i,t in enumerate(thresholds) if points>=t)
    return {'sandbox_spend_30d_paise':sandbox_spend,'sandbox_points':queries*10+sandbox_spend//1000,'tier':TIERS[level],'points':points,'meaningful_queries_30d':queries,'verified_spend_30d_paise':spend,'monthly_query_cap':100,
            'next_tier':TIERS[level+1] if level<3 else None,'next_threshold':thresholds[level+1] if level<3 else None,
            'rule':'10 points per unique meaningful query (same dish once per 24 hours, maximum 100 per 30 days), plus 1 point per ₹10 net verified spend. Simulations and receipts do not count.'}

def policy_check(db,user,campaign):
    policy=db.get(CampaignPolicy,campaign.id)
    if not policy:
        from types import SimpleNamespace
        policy=SimpleNamespace(min_tier='Bronze',cuisine='',cuisine_queries_30d=0,daily_budget_paise=200000,flat_discount_paise=0)
    state=tier_state(db,user.id);reasons=[]
    if TIERS.index(state['tier'])<TIERS.index(policy.min_tier):reasons.append(policy.min_tier+' tier required')
    if meaningful_queries(db,user.id,policy.cuisine)<policy.cuisine_queries_30d:reasons.append('More unique cuisine queries needed this month')
    week=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    if db.scalar(select(Redemption.id).where(Redemption.user_id==user.id,Redemption.campaign_id==campaign.id,Redemption.created_at>=week,active_reservations()).limit(1)):reasons.append('This offer was already reserved in the last seven days')
    # Restaurant-day limit uses Mumbai calendar dates and includes all its campaigns.
    from zoneinfo import ZoneInfo
    midnight=datetime.now(ZoneInfo('Asia/Kolkata')).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat()
    spent=db.scalar(select(func.coalesce(func.sum(Redemption.discount_paise),0)).join(Campaign,Campaign.id==Redemption.campaign_id).where(Campaign.restaurant_id==campaign.restaurant_id,Redemption.created_at>=midnight,active_reservations())) or 0
    shared_cap=db.scalar(select(func.min(CampaignPolicy.daily_budget_paise)).join(Campaign,Campaign.id==CampaignPolicy.campaign_id).where(Campaign.restaurant_id==campaign.restaurant_id,Campaign.starts_at<=now(),Campaign.ends_at>=now())) or policy.daily_budget_paise
    if spent>=shared_cap:reasons.append('Restaurant daily discount budget reached')
    return reasons,{'remaining_paise':max(0,shared_cap-spent),'flat_discount_paise':policy.flat_discount_paise}


def active_reservations():
    cancelled=select(DealVoucher.redemption_id).where(or_(DealVoucher.state=='cancelled',and_(DealVoucher.state=='pending',DealVoucher.expires_at<=now())))
    return Redemption.id.not_in(cancelled)
