from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.core.db import get_session
from app.core.cache import invalidate_project_sync
from app.models import Project, Environment, SDKKey, FeatureFlag, FeatureVariant, FeatureRule

router = APIRouter()


@router.post("/projects", response_model=Project)
def create_project(project: Project, session: Session = Depends(get_session)):
    session.add(project)
    session.commit()
    session.refresh(project)
    return project
"""
Post/project
yeni bir proje (örn: shop) oluşturup veritabanına kaydediyor.sonrada kaydettiği satırı geri dönderiyor.
"""

@router.get("/projects", response_model=list[Project])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project)).all()
"""
get/projects
db'deki tüm projeleri listeliyor.
"""


@router.post("/envs", response_model=Environment)
def create_env(env: Environment, session: Session = Depends(get_session)):
    if not session.get(Project, env.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        session.add(env)
        session.commit()
        session.refresh(env)
        invalidate_project_sync(env.project_id)
        return env
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Environment name already exists for this project")

"""
post/envs
yeni bir environment (ör: prod,dev) oluşturuyor.
oluşturma yapmadan önce project_id var mı yok mu kontrolu yapıyor(yoksa 404 fırlatıyor.)
models dosyamda yer alan environment tablomda bir kontrol eklemiştim,aynı özelliklere sahip bir satır eklendiğinde db IntegrityError fırlatıyordu,bu hatayı Fast API yakalıyordu ama 500(Internal Server Error) olarak
yakalıyordu,biz bu hatayı daha anlamlı bir hale getirebilmek için try extcept bloğu ekledik.
Güncelleme:
invalidate_project_sync(env.project_id) kod satırı env tablosunda herhangi bir değişiklik yapıtığımızda ilgili id'ye sahip olan json bilgilerini cache'den silmektedir.
"""

@router.get("/envs", response_model=list[Environment])
def list_envs(session: Session = Depends(get_session)):
    return session.exec(select(Environment)).all()
"""
Get/envs
tüm environment kayıların getirip listeliyor.
"""


@router.post("/keys", response_model=SDKKey)
def create_key(k: SDKKey, session: Session = Depends(get_session)):
    if not session.get(Project, k.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not session.get(Environment, k.environment_id):
        raise HTTPException(status_code=404, detail="Environment not found")
    try:
        session.add(k)
        session.commit()
        session.refresh(k)
        invalidate_project_sync(k.project_id)
        return k
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="SDK key already exists")
"""
Post/keys
yeni bir sdk key eklemesi yapıyoruz,ama eklemeyi tam yapmadan önce eklenecek olan projenin veya environment'in gerçekten var olup olmadığına bakıyoruz,
eğer yoksa hata fırlatıyoruz.
sonrasında ise ürünleri ekliyoruz,ama except içerisinde bir catch bloğu kontrolu yapıyoruz,eğer ki key varsa 409 hata kodu ile sdk key zaten var hatası fırlatıyoruz.
Güncelleme:invalidate_project_sync(k.project_id) satırı ilgili bilgileri cache'den siliyor.
"""

@router.get("/keys", response_model=list[SDKKey])
def list_keys(session: Session = Depends(get_session)):
    return session.exec(select(SDKKey)).all()
"""
Get/keys
tüm sdk key kayıtlarını getiriyoruz.
"""

@router.post("/flags", response_model=FeatureFlag)
def create_flag(flag: FeatureFlag, session: Session = Depends(get_session)):
    if flag.status not in {"draft", "active", "published"}:
        raise HTTPException(422, "Invalid status")
    if not session.get(Project, flag.project_id):
        raise HTTPException(404, "Project not found")
    try:
        session.add(flag); session.commit(); session.refresh(flag)
        invalidate_project_sync(flag.project_id)
        return flag
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Flag key already exists in this project")
"""
post/flags
istek gövdesindeki jsonu'u alıp featureFlag nesnesine çevirdikten sonra bir if koşulu içerisinde bu flag'ın içerisinde yer alan project_id'nin gerçekten var olup olmadığı kontrolunu yapıyoruz.varsa flag veri tabanına bilgileri yüklüyor
yoksa 404 hatası fırlatıyor.En sonunda ise db'nin verdiği id gibi alanları geri dönderiyor(json olarak)
Güncelleme:
ilk if kontrolu ile status alanına "draft", "active", "published" ifadelerinden başka bir şey yazldığında hata fırlatılmasını sağladık.
ek olarak aynı key değerine sahip olan herhangi bir satır eklendiği zaman 409 hatası fırlatıyoruz.
Güncelleme2:  invalidate_project_sync(flag.project_id) satırı ile ilgili bilgiler cache'den siliniyor.
"""

@router.get("/flags", response_model=list[FeatureFlag])
def list_flags(session: Session = Depends(get_session)):
    return session.exec(select(FeatureFlag)).all()
"""
get/flags
veritabanındaki tüm featureflag kayıtlarını json olarak listeliyor.
"""

class StatusUpdate(BaseModel):
    status: str
"""
istek gövdesinden yollanan status alanlarının doğru yazılıp yazılmadığını kontrol eden class yapısıdır,aşağıdaki metotta kullandık.
"""

@router.patch("/flags/{flag_id}/status", response_model=FeatureFlag)
def update_flag_status(flag_id: int, body: StatusUpdate, session: Session = Depends(get_session)):
    if body.status not in {"draft", "active", "published"}:
        raise HTTPException(422, "Invalid status")
    f = session.get(FeatureFlag, flag_id)
    if not f:
        raise HTTPException(404, "Flag not found")
    f.status = body.status
    session.add(f); session.commit(); session.refresh(f)
    invalidate_project_sync(f.project_id)
    return f
"""
bilgileri girilen satırın status'unu güncellemek için:
1-öncelikle gönderilen ifadenin "draft", "active", "published" olup olmadığına bakıyoruz,değilse hata fırlatıyoruz
2-id ile gerçekten böyle bir flag var mı kontrolu yapıyoruz.
3-ardından güncelleme işlemlerimizi yapıyoruz.
Güncelleme: invalidate_project_sync(f.project_id) satırı ile ilgili yenilenmiş bilgiler cache'den siliniyor.
"""

@router.post("/flags/{flag_id}/variants", response_model=FeatureVariant)
def create_variant(flag_id: int, v: FeatureVariant, session: Session = Depends(get_session)):
    f = session.get(FeatureFlag, flag_id)
    if not f:
        raise HTTPException(404, "Flag not found")
    if not v.name or v.name.strip() == "":
        raise HTTPException(422, "Variant name is required")
    v.flag_id = flag_id
    try:
        session.add(v); session.commit(); session.refresh(v)
        invalidate_project_sync(f.project_id)
        return v
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Variant name already exists for this flag")
"""
post/flags/{flag_id}/variants
url'deki flag_id'ye bir varyant eklemek için oluşturulmuş bir endpointtir.bu flag_id ye sahip herhangi bir satır bulunmuyorsa hata 404 fırlatıyor.
Güncelleme:
variant kısmına boş input girilmesi engellendi.
ilgili flagda zaten aynı variant varsa bu engellendi.
Güncelleme2:
yeni bir f değişkeni oluşturuldu.invalidate_project_sync(f.project_id) satırı ile cache'de ilgili veriler temizlendi.
"""
@router.get("/flags/{flag_id}/variants", response_model=list[FeatureVariant])
def list_variants(flag_id: int, session: Session = Depends(get_session)):
    return session.exec(select(FeatureVariant).where(FeatureVariant.flag_id == flag_id)).all()
"""
get/flags/{flag_id}/variants
url'deki flag_id'yi alıp featurevariant tablosundaki flag_id ile aynı olan bütün sonuçları getirir.
"""

# -------- Rules --------
def _validate_predicate(p: dict):
    if not isinstance(p, dict):
        raise HTTPException(422, "predicate must be an object")
    if "attr" not in p or "op" not in p or "value" not in p:
        raise HTTPException(422, "predicate must have attr, op, value")
    if p["op"] not in {"==", "in"}:
        raise HTTPException(422, "unsupported predicate op")
"""
bu metot aşağıda yer alan create_rule metotunu kullanarak FeatureRule tablosundaki predicate sütununa veri eklerken yukarıda yazdığımız koşulları kontrol eden metottur.
ilk if koşulu p'nin bir dict olması koşulunu tutuyor,yani yalnızca string,liste veya sayı gibi veri türü tutarsa bu durumda (predicate must be an object)yüklem bir nesne olmalıdır hatası fırlatıyoruz.
ikinci if koşulunda ise ilgili predicate sütununda yer alan dict'in içerisinde attr(attribute:"country","plan" vs.),op(operation:"==","in") ve value("TR",["TR","DE"]) alanlarının olup olmadığını kontrol ediyoruz,yoksa 
bu alanları içermeli diye bir hata veriyoruz.
op alanında izin verilen değerlerin yalnızca,"==" ve "in" olmasına izin veriyoruz,bunun dışında desteklenmeyen predicate hatası veriyoruz.
"""

def _validate_distribution(d: dict, allowed: set[str]):
    if not isinstance(d, dict) or not d:
        raise HTTPException(422, "distribution must be a non-empty object")
    total = 0
    for k, v in d.items():
        if k not in allowed:
            raise HTTPException(422, f"distribution key '{k}' not in {sorted(allowed)}")
        if not isinstance(v, int) or v < 0 or v > 100:
            raise HTTPException(422, "distribution values must be integers in [0,100]")
        total += v
    if total != 100:
        raise HTTPException(422, "distribution must sum to 100")
"""
-bu metot featurerule tablosundaki distrubtion alanınındaki verilerin doğruluğunu kontrol etmektedir.Yani bizim normalde bu alandaki verilerimiz hangi varyantı kullanıcıların yüzde kaçlık oranda kullancağını sorgulamak oluyor.
Bu yüzden bu satırımız { "A":30 ,  "off": 70} şeklinde örnek bir kullanıma sahip olmalıdır.
-metotumuzdaki parametrelere bakarsak: d harfi aşağıdaki createrule içerisindeki distrubtion alanını temsil ederken,allowed ise yine createrule metotu içerisindeki allowed tanımından gelmektedir ve içerisinde izin verilen variant
türleri bulunmaktadır.
-metotumuzun içeriğine bakarsak:
*ilk if koşulunda ilgili distribution sütununun bir dict yapısı şeklinde olup olmadığını veya boş olup olmadığı kontrolunu yapıyoruz.
*total ise yaptığımız paylaşamların toplam sayısını tutmaktadır.
*ardından elimizdeki verileri tek tek dolaışıyoruz.burdaki k varyant adını("A","off") tutarken v ise varyantın yüzdesini (30,70) tutmaktadır.
*bu for döngüsünün içerisindeki ilk if kontrolunde ekleyeceğimiz verideki varyant adının parametre olarak aldığımız allowed yapısının içerisinde olup olmadığına bakıyoruz.
*ikinci if koşulunda ise kullanıcının varyantları hangi yüzde ile kullanacağının koşulu yer almaktadır,yani sayıların int türünden ve 0 ile 100 arasında olmasını sağlıyoruz.
"en sonda ise bu yüzdeleri toplayıp değerinin yüz olup olmadığını kontrol ediyoruz.
"""

# ------- Rules -------
@router.post("/flags/{flag_id}/rules", response_model=FeatureRule)
def create_rule(flag_id: int, r: FeatureRule, session: Session = Depends(get_session)):
    f = session.get(FeatureFlag, flag_id)
    if not f:
        raise HTTPException(404, "Flag not found")
    if not session.get(Environment, r.environment_id):
        raise HTTPException(404, "Environment not found")
    _validate_predicate(r.predicate)

    existing = session.exec(
        select(FeatureVariant).where(FeatureVariant.flag_id == flag_id)
    ).all()
    allowed = {v.name for v in existing} | {f.default_variant}
    _validate_distribution(r.distribution, allowed)

    r.flag_id = flag_id
    session.add(r); session.commit(); session.refresh(r)
    invalidate_project_sync(f.project_id)
    return r
"""
post/flags/{flag_id}/rules
flag'e kural eklemek için oluşturulmuş endpointtir.
Url'de yer alan flag_id gerçekten var mı kontrolu yapılır,ardından bu kuralı kullanmak için yazdığımız ortam bu flag için var mı kontrolunu yapıyoruz,eğer ki bu if koşullarına 
girmezse de kuralımızı ekliyoruz.
Güncelleme:
-önceden direkt olarak yazdığımız session.get(FeatureFlag, flag_id) kod yapısını f değişkenine attık ki aşağıdaki kod yapılarında da bunu rahatlıkla kullanabilerim.
-eklenecek olan satırın predicate sütununun bilgileri doğtu formatta tanıyıp tanımadığını kontrol etmek için _validate_predicate(r.predicate) ile doğrulama metotunu çağırdık.
-existing alanında ise eklenecek olan flag'in id'sine göre ilgili satırın bütün verileri çekiliyor,sonrasında ise bu çekilen bilgiler bir for döngüsü ile dolaşılıyor ve name kısımları bir set haline getiriliyor
ardından varsayılan(ör:"off") default_variant ile de birleştirerek variant_isimlerini içerecek bir set yapısı elde etmiş oluyoruz,ve eklenecek olan verinin variant ismini ve yüzdesini kontrol etmek için gerekli
metotu çağırıyoruz.
Güncelleme2: invalidate_project_sync(f.project_id) satırı ile ilgili veriler cache'den silindi.
"""

@router.get("/flags/{flag_id}/rules", response_model=list[FeatureRule])
def list_rules(flag_id: int, session: Session = Depends(get_session)):
    return session.exec(select(FeatureRule).where(FeatureRule.flag_id == flag_id)).all()
"""
get/flags/{flag_id}/rules
url'deki flag_id'ye sahip olan tüm kuralları listeler.
"""