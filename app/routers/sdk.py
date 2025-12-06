from fastapi import APIRouter, Header, HTTPException, Query, Depends
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Environment, SDKKey, FeatureFlag, FeatureVariant, FeatureRule

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

    #Bu projenin flag'lerini getir
    flags = session.exec(
        select(FeatureFlag).where(
            FeatureFlag.project_id == sdk.project_id,
            FeatureFlag.status.in_(["active", "published"])
        )
    ).all()
    """
    yukarıda değerini aldığımız sdk'nin id'sine sahip olan tüm flag yapıların getiriyoruz.
    Güncelleme:
    -ek olarak sorguya status yapısı eklendi.böylece artık draft gibi flagler sdk'ya yönlendirilmeyecek.
    """

    out_flags = []
    for f in flags:
        # Variants
        variants = session.exec(
            select(FeatureVariant).where(FeatureVariant.flag_id == f.id)
        ).all()
        variants_map = {v.name: {"payload": v.payload} for v in variants} or {"off": {}}

        """
        her flag için oluşturduğumuz sözlükleri bir yapıda tutmak için yukarda out_flags adı ile boş bir dizi oluşturuyoruz.,sonrasında yukarıda tanımladığımız flagleri tek tek for döngüsü ile geziyoruz
        ve bu flag'lerin bütün varyantlarını çekiyoruz.
        variants_map kısmında ise verileri "off":  {"payload": {...}} şeklinde depoluyoruz.Bu kod yapısın açmak gerekirse:
        bu kod yapısı FetureVariant tablosundaki payload sütunundaki verileri çekiyor ve variants_map'e atıyor,eğer ki payload kısmı boş olan bir sütun varsa da varsayılan olark "off": {} atamasını yapıyoruz.
        """

        # Rules (sadece bu env)
        rules = session.exec(
            select(FeatureRule).where(
                FeatureRule.flag_id == f.id,
                FeatureRule.environment_id == environment.id
            )
        ).all()
        rules_out = [   #kuralları json şekline sokkuyoruz.
            {
                "priority": r.priority,
                "predicate": r.predicate,
                "distribution": r.distribution,
            }
            for r in rules
        ]

        out_flags.append({      #her flag için çıktı listesi oluşturuyoruz.
            "key": f.key,
            "on": f.on,
            "default_variant": f.default_variant,
            "variants": variants_map,
            "rules": rules_out,
            "status": f.status,
        })

    return {        #en sonunda sdk'nin kullanacağı tek bir json verisi şeklinde bilgileri geri dönderiyoruz.
        "env": env,
        "revision": "demo-rev",
        "flags": out_flags,
        "configs": {},
    }
