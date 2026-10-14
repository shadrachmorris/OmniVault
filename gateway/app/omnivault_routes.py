import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from app.config import settings
from app.middleware.auth_middleware import require_valid_token

router=APIRouter(prefix='/api/ov',tags=['OmniVault Goals, Insights & Shop'])
# Explicitly enumerate permitted operations; never allow arbitrary proxy paths.
RULES={
 ('GET','goals'):'goals', ('POST','goals'):'goals',
 ('PATCH','goals/{id}'):'goals/{id}', ('DELETE','goals/{id}'):'goals/{id}',
 ('POST','goals/{id}/contributions'):'goals/{id}/contributions',
 ('PATCH','budgets/{id}'):'budgets/{id}', ('DELETE','budgets/{id}'):'budgets/{id}',
 ('PATCH','transactions/{id}'):'transactions/{id}',
 ('POST','subscriptions/decision'):'subscriptions/decision', ('GET','subscriptions/decisions'):'subscriptions/decisions',
 ('GET','insights'):'insights',
 ('GET','shop/brands'):'shop/brands',('POST','shop/brands'):'shop/brands',
 ('GET','shop/preferences'):'shop/preferences',('POST','shop/preferences'):'shop/preferences',
 ('GET','shop/products'):'shop/products',('POST','shop/products'):'shop/products',
}
async def proxy(method,path,request,user):
    params=dict(request.query_params)
    params.pop('user_id',None)
    params['user_id']=user['user_id']
    payload=await request.json() if method in ('POST','PATCH') else None
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response=await client.request(method,settings.processing_service_url.rstrip('/')+'/ov/'+path,params=params,json=payload)
    except httpx.RequestError:
        raise HTTPException(503,'Finance service unavailable')
    try: result=response.json()
    except ValueError: result={'detail':response.text}
    if response.status_code>=400: raise HTTPException(response.status_code,result)
    return result

# Factory closure keeps routing configuration out of user-controlled query parameters.
def make_handler(method,path):
    async def handler(request:Request,user:dict=Depends(require_valid_token)):
        return await proxy(method,path,request,user)
    return handler

def make_id_handler(method,path):
    async def handler(id:int,request:Request,user:dict=Depends(require_valid_token)):
        return await proxy(method,path.replace('{id}',str(id)),request,user)
    return handler

for method,path in RULES:
    if '{id}' in path:continue
    router.add_api_route('/'+path,make_handler(method,path),methods=[method],name='ov_'+method+'_'+path.replace('/','_'))
for method,path in RULES:
    if '{id}' not in path:continue
    router.add_api_route('/'+path,make_id_handler(method,path),methods=[method],name='ov_'+method+'_'+path.replace('/','_'))

@router.post('/plaid/link-token')
async def plaid_link(request:Request,user:dict=Depends(require_valid_token)):
    return await plaid_proxy('POST','/plaid/link-token',request,user)
@router.post('/plaid/exchange-token')
async def plaid_exchange(request:Request,user:dict=Depends(require_valid_token)):
    return await plaid_proxy('POST','/plaid/exchange-token',request,user)
@router.post('/plaid/sync')
async def plaid_sync(request:Request,user:dict=Depends(require_valid_token)):
    return await plaid_proxy('POST','/plaid/sync',request,user)
async def plaid_proxy(method,path,request,user):
    params={'user_id':user['user_id']}
    body=await request.json() if path.endswith('exchange-token') else None
    try:
        async with httpx.AsyncClient(timeout=90 if path.endswith('sync') else 20) as client:
            response=await client.request(method,settings.processing_service_url.rstrip('/')+path,params=params,json=body)
    except httpx.RequestError: raise HTTPException(503,'Plaid processing unavailable')
    try: data=response.json()
    except ValueError:data={'detail':response.text}
    if response.is_error:raise HTTPException(response.status_code,data)
    return data
