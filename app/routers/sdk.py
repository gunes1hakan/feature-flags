from fastapi import APIRouter, Header, HTTPException, Query, Depends
from typing import Dict, Any, List
from collections import defaultdict
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.cache import cache_get_json, cache_set_json
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

    #Key bu env'e ait mi kontrolu
    sdk = session.exec(
        select(SDKKey).where(
            SDKKey.key == x_sdk_key)).first()
    if not sdk:
        raise HTTPException(status_code=401, detail="Invalid SDK key for this environment")
    """
    gönderdiğimiz key değerininin environment id değerini sdkkey tablosundan alıyoruz.
    eğer ki en yukarıda tanımladığımız get_flags ile aldığımız sdk_key değeri var ve de yukarıda env var mı kontrolu ile aldığımız environment değeri
    tabloda varsa ise ilgili satırı alıyoruz,yoksa 401 hatası ile de geçerli key girilmedi hatası fırlatıyoruz.
    """

    #Env var mı kontrolu
    environment = session.exec(
        select(Environment).where(
            Environment.name == env,
            Environment.project_id == sdk.project_id
        )
    ).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Unknown environment")
    """
    veritabanındaki environment tablosuna bakıyoruz:
    bu tabloda name=env olan satır var mı(ör: prod,dev) kontrolunu yapıyoruz.
    if kontrolu ile de aradığımız env yoksa 404 hatası fırlatıyoruz.
    """

    #Bu projenin flag'lerini getir
    flags = session.exec(
        select(FeatureFlag).where(
            FeatureFlag.project_id == sdk.project_id,
        )
    ).all()
    if not flags:
        return {"env": env, "project_id": sdk.project_id, "flags": []}
    flag_ids = [int(f.id) for f in flags if f.id is not None]
    """
    yukarıda değerini aldığımız sdk'nin id'sine sahip olan tüm flag yapıların getiriyoruz.
    Güncelleme:
    -ek olarak sorguya status yapısı eklendi.böylece artık draft gibi flagler sdk'ya yönlendirilmeyecek.
    Güncelleme2:
    -eğer ki herhangi bir flag yapısı yok ise geriye flag'i boş bir yapı olarak dönderip flag yapısının olmadığını gösteriyorum.
    -flag_ids kısmında bütün flagleri id'leri topluyoruz.
    """

    variants = session.exec(
        select(FeatureVariant).where(FeatureVariant.flag_id.in_(flag_ids))
    ).all()
    """
    burda önceki kod yapısında her bir sorgu için gidip database'i komple dolaşıp n+n+1 sorunu ile karşılaşma sorununu çözüyoruz,önce bu flag_ids'de tutulan tüm id'leri alıyoruz,sonrasında ise bu bilgiler ile bütün featureVariant'ları çekiyoruz.
    """
    variants_by_flag: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for v in variants:
        variants_by_flag[int(v.flag_id)][v.name] = v.payload or {}
    """
    yukarıdkai kod satırları flag_id --> variant_name --> payload şeklinde 3 katmanlı bir sözlük oluşturup tüm varyantları tek seferde gruplayıp,her flag için hızlıca variants alanını doldurabilmemizi sağlar.
    """

    rules = session.exec(
        select(FeatureRule)
        .where(
            FeatureRule.flag_id.in_(flag_ids),
            FeatureRule.environment_id == environment.id,
        )
        .order_by(FeatureRule.priority)
    ).all()

    rules_by_flag: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for r in rules:
        rules_by_flag[int(r.flag_id)].append({
            "priority": r.priority,
            "predicate": r.predicate or {},
            "distribution": r.distribution or {},
        })
    
    out_flags: List[Dict[str, Any]] = []
    for f in flags:
        out_flags.append({
            "key": f.key,
            "on": f.on,
            "default_variant": f.default_variant,
            "variants": variants_by_flag.get(int(f.id), {}),
            "rules": rules_by_flag.get(int(f.id), []),
            "configs": {},
        })


    return {"env": env, "project_id": sdk.project_id, "flags": out_flags}

"""
    cache_key = f"ff:flags:{sdk.project_id}:{environment.id}"
    cached = await cache_get_json(cache_key)
    if cached:
        return cached  # HIT
    
    ilk kod satırında yer alan cache_key oluşturulurken ilk olarak sdk.project_id ile sdk key'in bağlı olduğu projenin id'si alınıyor,environment.id ile bu isteğin geldiği environment.id alınıyor. ff:flags: ifadesi de sadece anlamlı bir 
    prefix ifadedir.
    ikinci kod satırı ile de oluşturduğumuz bu key değerini cache.py dosyasındaki cache_get_json() metotuna yaz diyoruz.böylece bu redise bu key ile kaydedilmiş herhangi json varsa alıyoruz.
    eğer önceden Redis'te hazırlanmış bir cevap varsa bunu geri dönderiyoruz yoksa DB'den verileri kendi almaya gidiyor.
    """

    

    

    
"""
    out_flags = []
    for f in flags:
        # Variants
        variants = session.exec(
            select(FeatureVariant).where(FeatureVariant.flag_id == f.id)
        ).all()
        variants_map = {v.name: {"payload": v.payload} for v in variants} or {"off": {}}

        
        her flag için oluşturduğumuz sözlükleri bir yapıda tutmak için yukarda out_flags adı ile boş bir dizi oluşturuyoruz.,sonrasında yukarıda tanımladığımız flagleri tek tek for döngüsü ile geziyoruz
        ve bu flag'lerin bütün varyantlarını çekiyoruz.
        variants_map kısmında ise verileri "off":  {"payload": {...}} şeklinde depoluyoruz.Bu kod yapısın açmak gerekirse:
        bu kod yapısı FetureVariant tablosundaki payload sütunundaki verileri çekiyor ve variants_map'e atıyor,eğer ki payload kısmı boş olan bir sütun varsa da varsayılan olark "off": {} atamasını yapıyoruz.
        

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

    resp = {
        "env": env,
        "revision": "demo-rev",
        "flags": out_flags,
        "configs": {},
    }    

    await cache_set_json(cache_key, resp, ttl_seconds=120)  # MISS → SET
    
    rediste bu bilgileri saklıyoruz.
    

    return resp #en sonunda sdk'nin kullanacağı tek bir json verisi şeklinde bilgileri geri dönderiyoruz."""
