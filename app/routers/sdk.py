from fastapi import APIRouter, Header, HTTPException, Query, Depends, Body
from typing import Dict, Any, List
from collections import defaultdict
from sqlmodel import Session, select
from app.core.db import get_session
from app.models import Environment, SDKKey, FeatureFlag, FeatureVariant, FeatureRule
from app.core.eval import evaluate_one_flag
from app.schemas import FlagsResponse, EvaluateUserIn, EvaluateResponse

router = APIRouter()

@router.get("/flags", response_model=FlagsResponse)
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

@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_flags(
    env: str = Query(..., description="Hedef ortam (örn: prod, dev, staging)"),
    x_sdk_key: str = Header(alias="X-SDK-Key"),
    user_in: EvaluateUserIn = Body(..., embed=False),
    session: Session = Depends(get_session),
):
    """
    main kısmında topladığımız endpointler admin endpointleridir,yani bilgi ekleme değiştirme gibi özellikleri bulunmaktadır,client(yani mobil,swagger) istemcilerden gelen get isteklerini ise ayrı bir sayfada toplamak istedik,
    işte bu endpointleri sdk.py dosyasında topladık,bu endpointleri main'deki endpointlerle birleştirmek için router kullanıyoruz,bu yüzden bu endpointlerimin başında @router ifadesi bulunmaktadır.
    bu routerların çağrısı main.py dosyamın içerisinde app.include_router(sdk.router, prefix="/sdk/v1", tags=["sdk"]) satırı ile toplanmaktadır.çünkü bizim router ifademizde main.py dosyasında olduğu gibi dış dünyaya fastapiyi
    kullanarak bağlanmamızı sağlayan app = FastAPI(title="Feature Flags & Remote Config", lifespan=lifespan) kodu yok,bu yüzden bu endpointleri main.py dosyası içerisindeki endpointlerle birleştirmemiz gerekiyor,işte bu yüzden
    app.include_router(sdk.router, prefix="/sdk/v1", tags=["sdk"]) bu kod satırını kullanıyoruz.Bu kod satırının detayına girersek bu satırın ilk parametresi der ki sdk.router endpointlerini al,ardından bu endpointin başına 
    2. parametre der ki /sdk/v1 ifadesini ekle,böylece endpoint ismimiz /sdk/v1/evaluate olur,3. parametresi ise bu endpointin swagger arayüzünde sdk adı altında toplanmasını sağlar.
    Şimdi bu metotun içerisine geçelim ve parametrelerini tek tek analiz edelim:
    env ifadesi gelen http isteğindeki env adlı  ifadeyi alıp env adlı değişkene atar,ör: POST /sdk/v1/evaluate?env=prod adlı bir http isteği geldi diyelim,bu isteğin sonundaki ? ifadesi http'nin ek olarak bir string ifade aldığını
    belirtir,bu string ifade de ise env=prod olarak tanımlanmış,yani bu örnek üzerinden ilerlersek parametre olan env değişkenine prod değerini atamış oluruz.description kısmı ise swagger'da açıklama eklememizi sağlamaktadır.
    ikinci parametre olan x_sdk_key'e geçersek.bu ifadede de gelen endpoint'teki Header verisini alıyor,bu satırı detaylı olarak açarsak,x_sdk_key'e gelecek olan değerin Header'dan geleceğini söylüyoruz yani url'den ya da query'den
    değil bu bilgiyi Header'dan alacaksın diyoruz,sonrasında ise bu bilgiyi X-SDK-Key adlı header'dan alacaksın diyoruz.
    şimdi metot içerisindeki 3. parametreye geçelim: bu parametre gelen user bilgilerini alıp bir dict'e atıyor.Body kısmına geçmeden önce şunu belirteyim,bu fonksiyonumuz bir post ifadesi olduğuna göre bir veri eklemesi yapacak,bu veriyi
    de alması gerekiyor,işte bu veriler FastAPI'de 3 yerden gelebilir,ya Query'den(ör: ?env:prod),ya Header'dan (ör: X-SDK-Key: demo3) ya da Body'den yani bir json gövdesinden gelir.işte biz burda user bilgilerini Body'den alacağız.
    . . . ifadesi Body'den gelen isteğin zorunlu olduğunu belirtiyor yani Body'den herhangi bir bilgi gelmezse geriye hata dönderirecek,embed=True ifadesi ise Body'den gelen bilginin user adı altında toplanmasını istiyor,yani normalde
    atıyorum body'den şöyle bir bilgi geliyor diyelim: {"country": "TR","is_premium": true,"user_id": "u123"} biz bu gelen veriyi {"user": { "country": "TR", "user_id": "u123" }} şeklinde alıyoruz,bu verileri user şeklinde gruplamamızın
    sebebi body'den gelen verilerin sadece user olarak gelmemesidir(örnek olarak verdiğimiz body'nin içeriğindeki bilgiler sadece user içeriyor ama altta daha geniş bir body verisi var),yani gelen bilgileri 
    {"user": { "country": "TR", "user_id": "u123" },"flag_keys": ["enable_dark_mode", "new_checkout"],"debug": true} şeklinde gruplandırırsak hangi
    bilginin neye ait olduğunu kolay bir şekilde anlıyoruz.Şimdi bilgiyi bu şekilde düzenledik diyelim: {"user": { "country": "TR", "user_id": "u123" }}.Ardından bu bilgiler dict'te depolanırken key değerleri user olmayacak yine normal
    key değerleri "country","user_id" olacakken,value değerleri "TR","u123" olacak.
    session ile de Db bağlantısı kurabilmek için FastAPI'nin bize verdiği bağlantı havuzundan bir tane db bağlantısını alıyoruz.
    Güncelleme:önceden kullanıcıdan aldığımız verileri dict ifadesi ile alıyorduk ama artık EvaluateUserIn class'ını kullanarak model şeklinde alıyoruz,ayriyeten artık embed'in true olmasına gerek kalmadı çünkü bu modelimizin kendisi
    user tagını verilerimizin önüne ekliyor,biz ekstra embed=true yaparsak içiçe iki tane user görüneceğinden çirkin bir görüntü ortaya çıkar.  
    """

    sdk = session.exec(select(SDKKey).where(SDKKey.key == x_sdk_key)).first()
    if not sdk:
        raise HTTPException(status_code=401, detail="Invalid SDK key")
    """
    yukarıdaki kod satırımız da ise parametre olarak aldığımız x_sdk_key değerini SDKKey adlı tabloda arıyoruz.kod satırına geçersek:
    select(SDKKey) ifadesi SDKKey adlı tablomuza gider,where(SDKKey.key==x_sdk_key) ifadesi ise bu SDKKey adlı tablodaki key adlı sütundaki değeri x_sdk_key olan verileri alır.exec() ifadesi girdiğimiz bu sorguyu sql cinsine çevirip 
    DB'de çalıştırır.session ifadesi de zaten db bağlantımızdı.first() ifadesi ise birden fazla veri gelirse ilk veriyi al diyoruz.(normalde zaten models.py içerisinde key: str = Field(index=True, unique=True) satırı ile bu key değerini
    benzersiz olarak alıyoruz yani zaten tek bir sonuç değeri geriye dönecek,ama olduda bir hata ile karşılaştık ya da oldu da key: str = Field(index=True, unique=True) kodundaki unique ifadesi silindi diyelim,bu durumları da düşünerek 
    güvenlik acısından ikinci bir doğrulama ekleyerek ilk veriyi aldık.
    """


    environment = session.exec(
        select(Environment).where(
            Environment.name == env,
            Environment.project_id == sdk.project_id
        )
    ).first()
    if not environment:
        raise HTTPException(status_code=404, detail="Unknown environment for this project")
    """
    project id'si project_id olan ama ortamı env olan bilgiyi Environment tablosundan alıp environment değişkenine atıyorum.
    """

    flags = session.exec(
        select(FeatureFlag).where(FeatureFlag.project_id == sdk.project_id)
    ).all()
    if not flags:
        return {"env": env, "project_id": sdk.project_id, "variants": {}}

    flag_ids = [int(f.id) for f in flags if f.id is not None]
    """
    burda flags içerisindeki verilerin id'sini toplayıp flag_ids adlı listeye atıyoruzki sürekli db'ye gitmeyelim.
    """

    variants = session.exec(
        select(FeatureVariant).where(FeatureVariant.flag_id.in_(flag_ids))
    ).all()
    variants_by_flag: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for v in variants:
        variants_by_flag[int(v.flag_id)][v.name] = v.payload or {}
    """
    bu kod yapısı yukarıda oluşturduğumuz flag_ids liste yapısının içerisindeki tüm flag_id'lerin FeatueVariant adlı tablodan bilgilerini getirir.
    sonrasında bu bilgileri bir dict'te tutalım diyoruz,bu tuttuğumuz dict ifadesinin ilk parametresi flag_id,ikinci içerdeki dict'in ilk parametresi variant ismini,içerdeki dict'in ilk parametresi ise payload'u tutsun dedik.eğer ki
    ardından bu variants bilgilerini dolaşarak variants_by_flag adlı sözlüğüme bu bilgileri yolluyorum.ör: flag_id=10, name="dark", payload={"btnColor":"green","font":"large"} diye bir tane db'den bilgi aldık diyelim,buna göre bu sözlük
    variants_by_flag(10)["dark"]="btnColor":"green","font":"large"} şeklinde bilgileri almış oluyor.
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

    """
    yukarıdaki ifade her bir flag_id için ve environment_id için kurallar ekliyor.bu kuralları rules_by_flag dict'inde toplayalım dedik ve rules içersiindeki bilgileri tek tek bu dict'e ekledik.
    """

    # 4) Her flag için tek bir varyant seç
    decided: Dict[str, str] = {}
    for f in flags:
        chosen = evaluate_one_flag(
            project_id=sdk.project_id,
            flag_key=f.key,
            default_variant=f.default_variant,
            rules=rules_by_flag.get(int(f.id), []),
            user=user_in.user,
        )
        decided[f.key] = chosen
    """
    yukarıdaki kod yapısı her flag için bir variant oluşturmamızı sağlıyor.bu variant'ları decided adlı bir sözlükte key,variant şeklinde bir key value ilişkisine göre tutacağız.
    ikinci satırda ise yukarıda aldığımız flags değerlerini tek tek dolaşıyoruz ve eval.py dosyasındaki evaluate_one_flag metotu ile flag değerine bir tane variant atıyoruz,sonrasında da bu variant'ı flag'in keyi ile birleştiriyoruz
    ve decided adlı sözlüğe yolluyoruz.
    Güncelleme:artık user ifadesini bir dict olarak değil de model olarak tuttuğumuz için model'ın adresini veriyorum.  
    """

    return {"env": env, "project_id": sdk.project_id, "variants": decided}
    #en sonda da bu bilgileri toplu olarak geri dönderiyoruz.

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
