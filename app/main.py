from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.core.db import init_db, get_session
from app.models import Project, Environment, SDKKey, FeatureFlag, FeatureVariant, FeatureRule
from app.routers import sdk

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Feature Flags & Remote Config", lifespan=lifespan)
"""
uygulama ilk ayağa kalkarken init_db() çağırıyor.
bu sayede tablolar oluşturuluyor ve db hazırlanıyor.
FastAPI kısmında ise parametre olarak yukarıda oluşturduğumuz lifespan'ı parametre olarak veriyoruz ve de başlangıçta bu işleri yap diyoruz.
"""

@app.get("/healthz")
def healthz():
    return {"ok": True}
"""
bu kısım sunucuyu ayağa kaldırdıktan sonra api çalışıyor mu diye kontrol ettimiz kısımdır.
Sunucuyu çağırdıktan sonra tarayıcının adres kısmına ilgili komutu girdikten sonra ekranda ok: true yazısı çıkıyorsa api'miz çalışıyor demektir.
"""

@app.post("/projects", response_model=Project)
def create_project(project: Project, session: Session = Depends(get_session)):
    session.add(project)
    session.commit()
    session.refresh(project)
    return project
"""
Post/project
yeni bir proje (örn: shop) oluşturup veritabanına kaydediyor.sonrada kaydettiği satırı geri dönderiyor.
"""

@app.get("/projects", response_model=list[Project])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project)).all()
"""
get/projects
db'deki tüm projeleri listeliyor.
"""


@app.post("/envs", response_model=Environment)
def create_env(env: Environment, session: Session = Depends(get_session)):
    if not session.get(Project, env.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    session.add(env)
    session.commit()
    session.refresh(env)
    return env
"""
post/envs
yeni bir environment (ör: prod,dev) oluşturuyor.
oluşturma yapmadan önce project_id var mı yok mu kontrolu yapıyor(yoksa 404 fırlatıyor.)
"""

@app.get("/envs", response_model=list[Environment])
def list_envs(session: Session = Depends(get_session)):
    return session.exec(select(Environment)).all()
"""
Get/envs
tüm environment kayıların getirip listeliyor.
"""


@app.post("/keys", response_model=SDKKey)
def create_key(k: SDKKey, session: Session = Depends(get_session)):
    if not session.get(Project, k.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.get(Environment, k.environment_id):
        raise HTTPException(status_code=404, detail="Environment not found")
    try:
        session.add(k)
        session.commit()
        session.refresh(k)
        return k
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="SDK key already exists")
"""
Post/keys
yeni bir sdk key eklemesi yapıyoruz,ama eklemeyi tam yapmadan önce eklenecek olan projenin veya environment'in gerçekten var olup olmadığına bakıyoruz,
eğer yoksa hata fırlatıyoruz.
sonrasında ise ürünleri ekliyoruz,ama except içerisinde bir catch bloğu kontrolu yapıyoruz,eğer ki key varsa 409 hata kodu ile sdk key zaten var hatası fırlatıyoruz.
"""

@app.get("/keys", response_model=list[SDKKey])
def list_keys(session: Session = Depends(get_session)):
    return session.exec(select(SDKKey)).all()
"""
Get/keys
tüm sdk key kayıtlarını getiriyoruz.
"""

@app.post("/flags", response_model=FeatureFlag)
def create_flag(flag: FeatureFlag, session: Session = Depends(get_session)):
    if not session.get(Project, flag.project_id):
        raise HTTPException(404, "Project not found")
    session.add(flag); session.commit(); session.refresh(flag)
    return flag
"""
post/flags
istek gövdesindeki jsonu'u alıp featureFlag nesnesine çevirdikten sonra bir if koşulu içerisinde bu flag'ın içerisinde yer alan project_id'nin gerçekten var olup olmadığı kontrolunu yapıyoruz.varsa flag veri tabanına bilgileri yüklüyor
yoksa 404 hatası fırlatıyor.En sonunda ise db'nin verdiği id gibi alanları geri dönderiyor(json olarak)
"""

@app.get("/flags", response_model=list[FeatureFlag])
def list_flags(session: Session = Depends(get_session)):
    return session.exec(select(FeatureFlag)).all()
"""
get/flags
veritabanındaki tüm featureflag kayıtlarını json olarak listeliyor.
"""

@app.post("/flags/{flag_id}/variants", response_model=FeatureVariant)
def create_variant(flag_id: int, v: FeatureVariant, session: Session = Depends(get_session)):
    if not session.get(FeatureFlag, flag_id):
        raise HTTPException(404, "Flag not found")
    v.flag_id = flag_id
    session.add(v); session.commit(); session.refresh(v)
    return v
"""
post/flags/{flag_id}/variants
url'deki flag_id'ye bir varyant eklemek için oluşturulmuş bir endpointtir.bu flag_id ye sahip herhangi bir satır bulunmuyorsa hata 404 fırlatıyor.
"""
@app.get("/flags/{flag_id}/variants", response_model=list[FeatureVariant])
def list_variants(flag_id: int, session: Session = Depends(get_session)):
    return session.exec(select(FeatureVariant).where(FeatureVariant.flag_id == flag_id)).all()
"""
get/flags/{flag_id}/variants
url'deki flag_id'yi alıp featurevariant tablosundaki flag_id ile aynı olan bütün sonuçları getirir.
"""

# ------- Rules -------
@app.post("/flags/{flag_id}/rules", response_model=FeatureRule)
def create_rule(flag_id: int, r: FeatureRule, session: Session = Depends(get_session)):
    if not session.get(FeatureFlag, flag_id):
        raise HTTPException(404, "Flag not found")
    if not session.get(Environment, r.environment_id):
        raise HTTPException(404, "Environment not found")
    r.flag_id = flag_id
    session.add(r); session.commit(); session.refresh(r)
    return r
"""
post/flags/{flag_id}/rules
flag'e kural eklemek için oluşturulmuş endpointtir.
Url'de yer alan flag_id gerçekten var mı kontrolu yapılır,ardından bu kuralı kullanmak için yazdığımız ortam bu flag için var mı kontrolunu yapıyoruz,eğer ki bu if koşullarına 
girmezse de kuralımızı ekliyoruz.
"""

@app.get("/flags/{flag_id}/rules", response_model=list[FeatureRule])
def list_rules(flag_id: int, session: Session = Depends(get_session)):
    return session.exec(select(FeatureRule).where(FeatureRule.flag_id == flag_id)).all()
"""
get/flags/{flag_id}/rules
url'deki flag_id'ye sahip olan tüm kuralları listeler.
"""

app.include_router(sdk.router, prefix="/sdk/v1", tags=["sdk"])
"""
SDK router'ı bağlama
Ayrı bir dosyada tanımladığın sdk router’ını ana uygulamaya bağlıyor.
Bu sayede:
/sdk/v1/flags gibi endpoint’ler aktif oluyor.
Swagger’da “sdk” diye ayrı bir grup altında görünüyor.
Özet: “Feature flags’i dış dünyaya servis eden asıl endpoint’leri” bu satır projeye takıyor.
"""