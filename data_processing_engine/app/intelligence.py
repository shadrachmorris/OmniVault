from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.finance_models import Account, Budget, Subscription, Transaction

router = APIRouter(prefix='/finance/intelligence', tags=['Financial Intelligence'])
D = Decimal

def money(value):
    return str(D(str(value)).quantize(D('0.01')))

@router.get('/overview')
async def overview(user_id: int, days: int = Query(30, ge=7, le=90), safety_balance: Decimal = Query(D('100'), ge=0), db: AsyncSession = Depends(get_db)):
    today = date.today()
    start = today - timedelta(days=days-1)
    transactions = (await db.execute(select(Transaction).where(Transaction.user_id == user_id, Transaction.transaction_date >= start, Transaction.transaction_date <= today, Transaction.pending.is_(False)))).scalars().all()
    accounts = (await db.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    budgets = (await db.execute(select(Budget).where(Budget.user_id == user_id))).scalars().all()
    subscriptions = (await db.execute(select(Subscription).where(Subscription.user_id == user_id, Subscription.is_active.is_(True)))).scalars().all()

    inflow = D('0'); outflow = D('0'); categories = defaultdict(lambda: D('0'))
    for tx in transactions:
        amount = D(str(tx.amount))
        if amount > 0:
            outflow += amount
            categories[(tx.category or 'Uncategorized').strip().lower()] += amount
        elif amount < 0:
            inflow += -amount

    balance = sum((D(str(a.balance)) for a in accounts), D('0'))
    daily_net = (inflow-outflow)/D(days)
    projected_balance = balance + daily_net * D(30)
    monthly_recurring = D('0'); upcoming = []; missing_dates = []
    for sub in subscriptions:
        amount = D(str(sub.amount))
        frequency = (sub.billing_frequency or 'monthly').lower()
        factor = {'weekly': D('52')/D('12'), 'biweekly': D('26')/D('12'), 'monthly': D('1'), 'quarterly': D('1')/D('3'), 'yearly': D('1')/D('12'), 'annual': D('1')/D('12')}.get(frequency)
        if factor is not None:
            monthly_recurring += amount*factor
        if sub.next_billing_date is None:
            missing_dates.append({'id':sub.id,'name':sub.name})
        elif today <= sub.next_billing_date <= today+timedelta(days=30):
            upcoming.append({'id':sub.id,'name':sub.name,'amount':money(amount),'date':sub.next_billing_date.isoformat()})
    upcoming.sort(key=lambda s:s['date'])

    alerts = []
    if projected_balance < safety_balance:
        alerts.append({'severity':'warning','title':'Projected low balance','detail':f'At the current historical pace, your 30-day estimate is ${money(projected_balance)}, below your ${money(safety_balance)} threshold.'})
    for budget in budgets:
        category = (budget.category or '').strip().lower()
        limit = D(str(budget.monthly_limit))
        # Budget warnings use the calendar month, not an arbitrary rolling window.
        month_spend = sum((D(str(t.amount)) for t in transactions if t.transaction_date >= today.replace(day=1) and D(str(t.amount)) > 0 and (t.category or '').strip().lower() == category), D('0'))
        if limit > 0 and month_spend >= limit * D('0.8'):
            alerts.append({'severity':'warning' if month_spend > limit else 'notice','title':f'{budget.category} budget','detail':f'${money(month_spend)} spent of ${money(limit)}.'})
    if missing_dates:
        alerts.append({'severity':'notice','title':'Missing subscription dates','detail':f'{len(missing_dates)} active subscriptions have no next billing date.'})
    if len(transactions) < 20:
        alerts.append({'severity':'info','title':'Limited transaction history','detail':'This analysis is based on fewer than 20 posted transactions; projections may be unstable.'})
    if not alerts:
        alerts.append({'severity':'info','title':'No immediate alerts','detail':'No configured thresholds were triggered.'})

    savings_rate = (inflow-outflow)/inflow*D(100) if inflow > 0 else None
    return {
        'user_id':user_id, 'period_days':days, 'transactions_analyzed':len(transactions),
        'cash_flow':{'inflow':money(inflow),'spending':money(outflow),'net':money(inflow-outflow),'savings_rate_percent':round(float(savings_rate),1) if savings_rate is not None else None},
        'balance':{'current':money(balance),'estimated_in_30_days':money(projected_balance),'safety_threshold':money(safety_balance)},
        'top_spending_categories':[{'category':key,'amount':money(value)} for key,value in sorted(categories.items(),key=lambda item:item[1],reverse=True)[:5]],
        'subscriptions':{'active_count':len(subscriptions),'estimated_monthly_cost':money(monthly_recurring),'upcoming_30_days':upcoming,'missing_billing_dates':missing_dates},
        'alerts':alerts,
        'method':'Rule-based historical analysis. Positive transactions treated as spending; negative as inflows.',
        'limitations':['Refunds and account transfers may distort cash flow.','Monthly budget checks may be incomplete when the requested period starts after the first of the month.','Subscriptions are displayed separately, not subtracted again from historical spending.','Account balances may double-count accounts that represent the same real-world funds.','Forecasts are estimates, not guaranteed balances.']
    }
