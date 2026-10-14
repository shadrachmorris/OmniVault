from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.finance_models import Account, Budget, Brand, Subscription, Transaction, UserBrandPreference
from app.omnivault_models import SavingsGoal, GoalContribution, Product, SubscriptionDecision

router = APIRouter(prefix='/ov', tags=['OmniVault Extended Features'])
D = Decimal

def cash(n): return str(D(str(n)).quantize(D('.01'), rounding=ROUND_HALF_UP))
def normalize(s): return ' '.join(s.lower().strip().split())
def safe_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.hostname in {'localhost','127.0.0.1'}:
        raise HTTPException(422, 'A public HTTPS URL is required')
    return url

class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    target_date: date | None = None
class GoalEdit(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    target_date: date | None = None
class ContributionIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
class BudgetEdit(BaseModel):
    monthly_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
class TransactionEdit(BaseModel):
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=255)
class DecisionIn(BaseModel):
    merchant_name: str = Field(min_length=1, max_length=150)
    decision: str = Field(pattern='^(confirmed|rejected|review)$')
class BrandIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: str | None = None
    website: str | None = None
class PreferenceIn(BaseModel):
    brand_id: int
    score: Decimal = Field(ge=0, le=100)
class ProductIn(BaseModel):
    brand_id: int
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    product_url: str
    image_url: str | None = None

def goal_dict(g):
    t=D(g.target_amount); s=D(g.saved_amount)
    return {'id':g.id,'name':g.name,'target_amount':cash(t),'saved_amount':cash(s),'remaining':cash(max(D(0),t-s)), 'progress_percent':round(float(s/t*100),2),'target_date':g.target_date.isoformat() if g.target_date else None}
async def owned_goal(db,user_id,goal_id):
    g=(await db.execute(select(SavingsGoal).where(SavingsGoal.user_id==user_id,SavingsGoal.id==goal_id))).scalar_one_or_none()
    if not g: raise HTTPException(404,'Savings goal not found')
    return g

@router.get('/goals')
async def goals(user_id:int, db:AsyncSession=Depends(get_db)):
    gs=(await db.execute(select(SavingsGoal).where(SavingsGoal.user_id==user_id).order_by(SavingsGoal.id.desc()))).scalars().all()
    return {'goals':[goal_dict(g) for g in gs]}
@router.post('/goals',status_code=201)
async def create_goal(user_id:int, body:GoalIn, db:AsyncSession=Depends(get_db)):
    g=SavingsGoal(user_id=user_id,**body.model_dump()); db.add(g); await db.commit(); await db.refresh(g); return goal_dict(g)
@router.patch('/goals/{goal_id}')
async def edit_goal(goal_id:int,user_id:int,body:GoalEdit,db:AsyncSession=Depends(get_db)):
    g=await owned_goal(db,user_id,goal_id)
    for k,v in body.model_dump(exclude_unset=True).items():
        if k in ('name','target_amount') and v is None: raise HTTPException(422,f'{k} cannot be null')
        setattr(g,k,v)
    await db.commit(); await db.refresh(g); return goal_dict(g)
@router.post('/goals/{goal_id}/contributions',status_code=201)
async def contribute(goal_id:int,user_id:int,body:ContributionIn,db:AsyncSession=Depends(get_db)):
    g=await owned_goal(db,user_id,goal_id)
    g.saved_amount=D(g.saved_amount)+body.amount
    db.add(GoalContribution(goal_id=goal_id,user_id=user_id,amount=body.amount))
    await db.commit(); await db.refresh(g)
    return {'goal':goal_dict(g),'note':'Recorded as goal progress only; no bank transfer was initiated.'}
@router.delete('/goals/{goal_id}')
async def delete_goal(goal_id:int,user_id:int,db:AsyncSession=Depends(get_db)):
    g=await owned_goal(db,user_id,goal_id)
    for c in (await db.execute(select(GoalContribution).where(GoalContribution.goal_id==g.id))).scalars(): await db.delete(c)
    await db.delete(g); await db.commit(); return {'deleted':True}

@router.patch('/budgets/{budget_id}')
async def edit_budget(budget_id:int,user_id:int,body:BudgetEdit,db:AsyncSession=Depends(get_db)):
    b=(await db.execute(select(Budget).where(Budget.id==budget_id,Budget.user_id==user_id))).scalar_one_or_none()
    if not b: raise HTTPException(404,'Budget not found')
    b.monthly_limit=body.monthly_limit; await db.commit(); return {'id':b.id,'category':b.category,'monthly_limit':cash(b.monthly_limit)}
@router.delete('/budgets/{budget_id}')
async def delete_budget(budget_id:int,user_id:int,db:AsyncSession=Depends(get_db)):
    b=(await db.execute(select(Budget).where(Budget.id==budget_id,Budget.user_id==user_id))).scalar_one_or_none()
    if not b: raise HTTPException(404,'Budget not found')
    await db.delete(b); await db.commit(); return {'deleted':True}
@router.patch('/transactions/{transaction_id}')
async def edit_transaction(transaction_id:int,user_id:int,body:TransactionEdit,db:AsyncSession=Depends(get_db)):
    t=(await db.execute(select(Transaction).where(Transaction.id==transaction_id,Transaction.user_id==user_id))).scalar_one_or_none()
    if not t: raise HTTPException(404,'Transaction not found')
    if not body.model_fields_set: raise HTTPException(422,'No changes supplied')
    if 'category' in body.model_fields_set: t.category=body.category
    if 'description' in body.model_fields_set:
        if body.description is None: raise HTTPException(422,'Description cannot be null')
        t.description=body.description
    await db.commit(); return {'id':t.id,'category':t.category,'description':t.description}

@router.post('/subscriptions/decision')
async def subscription_decision(user_id:int,body:DecisionIn,db:AsyncSession=Depends(get_db)):
    key=normalize(body.merchant_name)
    row=(await db.execute(select(SubscriptionDecision).where(SubscriptionDecision.user_id==user_id,SubscriptionDecision.merchant_key==key))).scalar_one_or_none()
    if row: row.decision=body.decision
    else: db.add(SubscriptionDecision(user_id=user_id,merchant_key=key,decision=body.decision))
    await db.commit(); return {'merchant_name':body.merchant_name,'decision':body.decision,'note':'A classification decision, not merchant cancellation.'}
@router.get('/subscriptions/decisions')
async def subscription_decisions(user_id:int,db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(SubscriptionDecision).where(SubscriptionDecision.user_id==user_id))).scalars().all()
    return {'decisions':[{'merchant_key':r.merchant_key,'decision':r.decision} for r in rows]}

@router.get('/insights')
async def insights(user_id:int,db:AsyncSession=Depends(get_db)):
    today=date.today(); start=today.replace(day=1)
    tx=(await db.execute(select(Transaction).where(Transaction.user_id==user_id,Transaction.transaction_date>=start,Transaction.transaction_date<=today,Transaction.pending.is_(False)))).scalars().all()
    budgets=(await db.execute(select(Budget).where(Budget.user_id==user_id))).scalars().all()
    subs=(await db.execute(select(Subscription).where(Subscription.user_id==user_id,Subscription.is_active.is_(True)))).scalars().all()
    spent={}
    for t in tx:
        amount=D(t.amount)
        if amount>0:
            key=normalize(t.category or 'uncategorized');spent[key]=spent.get(key,D(0))+amount
    cards=[]
    for b in budgets:
        used=spent.get(normalize(b.category),D(0)); limit=D(b.monthly_limit)
        if used>limit: cards.append({'level':'warning','title':f'{b.category} budget exceeded','message':f'You spent ${cash(used)} against a ${cash(limit)} limit.'})
        elif limit>0 and used>=limit*D('.8'): cards.append({'level':'notice','title':f'{b.category} budget approaching limit','message':f'You have ${cash(limit-used)} remaining.'})
    undated=sum(1 for s in subs if not s.next_billing_date)
    if undated: cards.append({'level':'notice','title':'Subscription dates missing','message':f'{undated} active subscription(s) need a renewal date to appear in upcoming bills.'})
    if not tx: cards.append({'level':'info','title':'More history needed','message':'There are no qualifying transactions this month. Insights will improve as your data grows.'})
    if not cards: cards.append({'level':'info','title':'No immediate budget warnings','message':'No tracked budget has crossed 80% based on current-month transactions.'})
    return {'user_id':user_id,'generated_on':today.isoformat(),'insights':cards,'method':'Transparent rules; no external AI model used.'}

@router.get('/shop/brands')
async def brands(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Brand).order_by(Brand.name))).scalars().all()
    return {'brands':[{'id':b.id,'name':b.name,'category':b.category,'website':b.website} for b in rows]}
@router.post('/shop/brands',status_code=201)
async def create_brand(body:BrandIn,db:AsyncSession=Depends(get_db)):
    b=(await db.execute(select(Brand).where(func.lower(Brand.name)==body.name.strip().lower()))).scalar_one_or_none()
    if b: return {'id':b.id,'name':b.name,'already_exists':True}
    b=Brand(name=body.name.strip(),category=body.category,website=safe_url(body.website) if body.website else None)
    db.add(b);await db.commit();await db.refresh(b);return {'id':b.id,'name':b.name}
@router.post('/shop/preferences')
async def preference(user_id:int,body:PreferenceIn,db:AsyncSession=Depends(get_db)):
    b=await db.get(Brand,body.brand_id)
    if not b: raise HTTPException(404,'Brand not found')
    p=(await db.execute(select(UserBrandPreference).where(UserBrandPreference.user_id==user_id,UserBrandPreference.brand_id==body.brand_id))).scalar_one_or_none()
    if p: p.score=body.score;p.preference_source='manual'
    else: db.add(UserBrandPreference(user_id=user_id,brand_id=body.brand_id,score=body.score,preference_source='manual'))
    await db.commit();return {'brand_id':body.brand_id,'score':cash(body.score)}
@router.get('/shop/preferences')
async def preferences(user_id:int,db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(UserBrandPreference,Brand).join(Brand,UserBrandPreference.brand_id==Brand.id).where(UserBrandPreference.user_id==user_id))).all()
    return {'preferences':[{'brand_id':b.id,'name':b.name,'score':cash(p.score)} for p,b in rows]}
@router.post('/shop/products',status_code=201)
async def create_product(body:ProductIn,db:AsyncSession=Depends(get_db)):
    if not await db.get(Brand,body.brand_id):raise HTTPException(404,'Brand not found')
    p=Product(**{**body.model_dump(),'product_url':safe_url(body.product_url),'image_url':safe_url(body.image_url) if body.image_url else None})
    db.add(p);await db.commit();await db.refresh(p);return {'id':p.id,'name':p.name}
@router.get('/shop/products')
async def products(user_id:int,category:str|None=None,max_price:Decimal|None=Query(default=None,ge=0),db:AsyncSession=Depends(get_db)):
    q=select(Product,Brand).join(Brand,Product.brand_id==Brand.id).where(Product.is_active.is_(True))
    if category:q=q.where(func.lower(Product.category)==category.lower())
    if max_price is not None:q=q.where(Product.price<=max_price)
    rows=(await db.execute(q.limit(100))).all()
    prefs=(await db.execute(select(UserBrandPreference).where(UserBrandPreference.user_id==user_id))).scalars().all()
    scores={p.brand_id:float(p.score) for p in prefs}
    out=[{'id':p.id,'name':p.name,'brand':b.name,'brand_id':b.id,'category':p.category,'price':cash(p.price),'product_url':p.product_url,'image_url':p.image_url,'preference_score':scores.get(b.id,0)} for p,b in rows]
    out.sort(key=lambda p:(-p['preference_score'],D(p['price'])))
    return {'products':out,'disclaimer':'Catalog entries are supplied by users/admins, not verified live retailer inventory or prices.'}
