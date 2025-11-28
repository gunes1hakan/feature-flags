from fastapi import APIRouter, Header, HTTPException, Query, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Environment, SDKKey

router = APIRouter()

@router.get("/flags")
async def get_flags(
    env: str = Query(..., description="Hedef ortam (örn: prod, dev, staging)"),
    x_sdk_key: str = Header(alias="X-SDK-Key"),
    session: Session = Depends(get_session),
):
    """
    GET /sdk/v1/flags    
    yukarıdaki kod yapısında diyoruz ki env ile query string'ten gelen bilgiyi al(env=prod gibi)
    x_sdk_key ile de header'den gelen veriyi al(ör: X-SDK-Key: demo)
    session: get_session sayesinde bize verilen veritabanı oturumunu alıyoruz.
    """
    #Env var mı kontrolu
    environment = session.exec(
        select(Environment).where(Environment.name == env)
    ).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Unknown environment")
    """
    veritabanındaki environment tablosuna bakıyoruz:
    bu tabloda name=env olan satır var mı(ör: prod,dev) kontrolunu yapıyoruz.
    if kontrolu ile de aradığımız env yoksa 404 hatası fırlatıyoruz.
    """

    #Key bu env'e ait mi kontrolu
    sdk = session.exec(
        select(SDKKey).where(
            SDKKey.key == x_sdk_key,
            SDKKey.environment_id == environment.id,
        )
    ).first()
    if not sdk:
        raise HTTPException(status_code=401, detail="Invalid SDK key for this environment")
    """
    gönderdiğimiz key değerininin environment id değerini sdkkey tablosundan alıyoruz.
    eğer ki en yukarıda tanımladığımız get_flags ile aldığımız sdk_key değeri var ve de yukarıda env var mı kontrolu ile aldığımız environment değeri
    tabloda varsa ise ilgili satırı alıyoruz,yoksa 401 hatası ile de geçerli key girilmedi hatası fırlatıyoruz.
    """

    #Şimdilik bütün bilgiler doğru kabul edip demo yanıt veriyoruz.(ileride flag/variant/rule ile dolduracağız)
    return {
        "env": env,
        "revision": "demo-rev",
        "flags": [{
            "key": "new_checkout",
            "on": True,
            "default_variant": "off",
            "variants": {"off": {}, "A": {"payload": {"btnColor": "green"}}},
            "rules": [{
                "priority": 1,
                "predicate": {"attr": "country", "op": "==", "value": "TR"},
                "distribution": {"A": 30, "off": 70},
            }],
        }],
        "configs": {},
    }
