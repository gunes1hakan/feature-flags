import hashlib
from typing import Dict, Any

"""
kullanıcının hangi varyantı kullanacağı bilgisini tuttuğumuz dosya yapısıdır.
"""


def _hash_to_bucket(seed: str) -> int:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100
"""
bu metotumuzun amacı gelen kullanıcıya rastgele bir sayı verip bu aldığı sayının aralığını göre de bu kullanıcıya varyant(dark,light vb.) vermektir.Kod yapısını analiz edersek:
öncelikle metot içerisinde bir seed(f"{project_id}:{flag_key}:{user.get('user_id') or str(user)}" gibi) alacağımızı ve geriye int değer döndereceğimizi bildiriyoruz.ardından bu gelen seed'i sha256 yöntemi ile hashliyoruz.
Bu elde ettiğimiz h değişkeninin içerisindeki ilk 8 karakteri alıyoruz ve 16'lık tabanda bir sayıya çeviriyoruz.
"""


def _matches(user: Dict[str, Any], predicate: Dict[str, Any]) -> bool:

    if not predicate:
        return False
    attr = predicate.get("attr")
    op = predicate.get("op")
    value = predicate.get("value")
    left = user.get(attr)

    if op == "==":
        return left == value
    if op == "!=":
        return left != value
    if op == "in":
        return left in (value or [])
    if op == "not_in":
        return left not in (value or [])
    if op == ">":
        return isinstance(left, (int, float)) and isinstance(value, (int, float)) and left > value
    if op == ">=":
        return isinstance(left, (int, float)) and isinstance(value, (int, float)) and left >= value
    if op == "<":
        return isinstance(left, (int, float)) and isinstance(value, (int, float)) and left < value
    if op == "<=":
        return isinstance(left, (int, float)) and isinstance(value, (int, float)) and left <= value
    return False

"""
bu metotum kullanıcının bilgilerinin gelen predicate bilgisine(rule tablosundaki bir sütundur.) uyup uymadığı kontrolu sağlıyorum.
öncelikle eğer ki karşılaştıracağım içi boş bir kural yanlışlıkla yollanmışsa ilk if koşulumda direkt bunu false olarak geri dönderiyorum.
sonrasında ise karşılaştırma yapacağım ifadeleri ilk olarak alıyorum.örnek user ve predicate dict'leri:
user: {"country": "TR", "age": 25, "is_premium": True}
predicate: {"attr": "country", "op": "==", "value": "TR"}
sonrasında ise attr,op,value ve left bilgilerini dolduruyorum:
attr="country"
op="=="
value="TR"
left=user.get(attr)=user.get("country")="TR"
bu değişkenlerime bilgileri doldurtuktan sonra user ile predicate içerisindeki value'lerin uyuşup uyuşmadığı kontrollerini yapıyorum:
op ifademin eşiti "==" olduğu için ilk if ifadesine girdi,sonrasında ise left'in value'ye eşit olup olmadığına baktık ve eşit olduğu için user kurala uyuyor manasında geriye true değerini dönderdik.
-in ve not_in kontrollerinde value'nun yanında ekstra bir de boş bir liste yapısı koyduk yani kurallar içerisinde herhangi bir dizi yapısı yok ve değeri none ise hata yaşamamak için boş bir liste yapısı varmış gibi tanımlıyoruz.
-<,>,>=,<= operatörlerini kullandığım yerlerde ekstra olarak tür kontrolu da yapıyorum yani yanlışlıkla veri girilirken örneğin {"attr": "age", "op": ">", "value": "18"} böyle bir predicate alındığında hata ile karşılaşırız çünkü value değeri string
olarak oluşturulmuş.
"""


def _pick_variant(distribution: Dict[str, Any], seed: str) -> str | None:
    if not distribution:
        return None

    total = 0.0
    normalized: Dict[str, float] = {}
    for name, weight in distribution.items():
        try:
            w = float(weight)
        except Exception:
            w = 0.0
        w = max(0.0, w)
        normalized[name] = w
        total += w

    if total <= 0.0:
        return None

    bucket = _hash_to_bucket(seed)
    threshold = 0.0
    for name, w in normalized.items():
        threshold += (w / total) * 100.0
        if bucket < threshold:
            return name

    return list(normalized.keys())[-1]

"""
öncelikle def_matches metotu ile kullanıcının kurala uyup uymadığını kontrol ettim,bu kontrol yaptıktan sonra bu kullanıcının hangi varyantı kullanacağı adımına geçtim,işte bu adımda pick_variant metotunda tespit ediliyor.
adım adım kod yapısından gidersek:
öncelikle metot distribution adı altında bir dict alıyor (ör: {"dark": 30, "off": 70}) ve kullanıcının hangi varyantı kullanacağı tespitini yapabilmek için kullanıcının bazı bilgilerini içeren bir metin yani seed alıyoruz.
ardından metot içeriğine geçiyoruz,ilk if koşulunda ise gelen distribution dict'nin boş ya da none olma durumunu kontrol ediyorum,eğer bu kurala uyan bir dict gelirse geriye none olarak dönderiyorum.(daha sonrasında bu none kontrolunu yapıp
defatult bir variant ataması yapacağım.)
total değişkeni ise bizim distrubtion dictinde gelen varyantların toplam ağırlığını tutuyor.
normalized dict'i ise bizim distrubtion içerisinde aldığımız verileri key value gibi kullanmamızı sağlıyor.bizim ekstra bir dict oluşturmamımızın sebebi distrubtion dictinde gelen ikinci verilerin türünün int mi,float mı ya da belki de string mi
olduğunu bilmememeizden dolayı ve dağılım işlemlerini daha rahat yapabilmek için dict ifadesindeki 2. parametrenin float olmasını istememizdir.
Ardından distrubtion içeriğindeki verileri eleman eleman geziyoruz.(döngüdeki elemanlardan örneğin name:dark olacakken weight'te 30 oluyor.)
ilk olarak yüzdemizi içerecek olan ikinci verileri float türünde bir sayıya çeviriyoruz.eğer ki bu sayı çevirme işlemi sırasında herhangi bir hata ile karşılaşırsak w ifadesini 0 olarak atıyoruz.
ardından w ifadesi hata fırlatmasa bile negatif değer de alabiliyor,biz de negatif bir değer istemediğimiz için bunu 0 yapıyoruz,eğer ki gelen değer negatif değilse olduğu değeri aynen alıyor.
ardından normalized dict'imin içerisine verimi key value ilişkisine uygun olacak şekilde atıyorum.(ör: normalized[dark]=30 oluyor ve normalized dict'i içerisinde bilgiler {"dark":30.0} şeklinde tutuluyor.)
sonrasında ise bu değerleri total değişkeni içerisinde topluyorum.
eğer ki bana gelen verilerin tümünün value değeri bozuksa ya da dönüştürme işlemi sırasında bir hata yaşıyorsam oto olarak hepsinin w değeri 0 olacak ve total değeri de 0 olacak.Bu durumda tekrardan none diyerek fonksiyonu sonlandırıyoruz
ve her birine default değer ataması yapıyoruz.
Kullanıcının hangi varyantı kullanacağını belirlemek için bir sayı üzerinden ilerlemeyi düşünüyoruz,yani örneğin metota parametre yollarken distrubtion için {"dark": 30, "half_dark":50, "off": 20} dict'ini yolladık diyelim.bu durumda bucket'tan
gelen değer 0-29 arasında ise dark,29-79 arasında ise half_dark,79-99 arasında ise off variant'ı almasını sağlıyorum.
yukarıdaki ifadeyi sağlamak için her kullanıcıya özgü diğer kullanıcılardan mümkün olduğunca farklı bir sayı vermek istiyorum ama bunun için random sınıfını kullanırsam aynı kullanıcı için tekrardan bir çağrı yaptığımda bu sefer farklı bir bucket
değeri çıkacağından farklı bir varyant alma özelliği doğuyor,bu sebepten hem değerin değişmemesi hem de mümkün olduğunca her kullanıcı için farklı bir sayı üretmek için sha256 metotunu kullanarak bir sayı üretmeye çalışıyorum,bunun için bu seed
değerimi _hash_to_bucket metotuma yolladıktan sonra gelen değeri bucket değişkenime atıyorum,ardından yukarıda bahsettiğim şu şu aralıkta şu varyant olsun ifademi yapabilmek için varyant değerlerini tek tek toplayacak threshold adında bir değişken
oluştuyorum.Ardından normalized dict'i içeriğindeki tüm bilgilerimi tek tek dolaşıyorum:
öncelikle distribution sözlüğünden gelen value değerlerinin yüzdelik dilimde oluşmayacağını bilmem gerekiyor,yani belki dict ifadesinin içi {"dark": 0.3, "half_dark": 0.2 , "off": 0.5} gibi ondalık sayılardan oluşacak.İşte bu durumlarında oluşabileceğini
düşünüp direkt threshold+=w demek yerine formülü threshold += (w / total) * 100.0 şeklinde yazıyoruz.Ardından kontrollerimizi tek tek yapıyoruz,örnek olması açısından {"dark": 30, "half_dark":20, "off": 50} dicti ile ilerleyelim:
bucket'tan 13 değeri geldi diyelim,for döngüsünde ilk olarak alınan değerler name="dark" w=30 değerleridir.buna göre threshold değeri 30 olur.Altındaki if kuralına baktığımız da ise 13<30 olduğundan return "dark" denilerek metottan çıkarız.başka bir örnek:
bucket=75 olsun,for döngüsünde ilk olarak alınan değerler name="dark" w=30 değerleridir.buna göre threshold değeri 30 olur.Altındaki if kuralına baktığımız da ise 75<30 olmadığından ife girmeyiz ve döngü devam eder,normalized içeriğindeki ikinci veri olan
name="half_dark" w=20 değeri alınır.buna göre threshold=30+20'den 50 gelir,altındaki if koşulunu da sağlamadığından for döngüsüne devam ederiz ve son koşulu da sağladıktan sonra geriye off cevabını döneriz.
oldu da float türüne çevirme işlemi sırasında float taşması gibi durumlar oldu ve saçma sayılar çıktı,bu durumdan dolayı da if ifadelerine girmedi diyelim kullanıcı,bu durumda kullanıcıya distribution sözlüğü içerisindeki sonununcu elemanın varyantını
atıyoruz.
"""


def evaluate_one_flag(
    *,
    project_id: int,
    flag_key: str,
    default_variant: str,
    rules: list[dict],
    user: Dict[str, Any],
) -> str:

    base_seed = f"{project_id}:{flag_key}:{user.get('user_id') or str(user)}"

    for r in rules:
        if _matches(user, r.get("predicate") or {}):
            chosen = _pick_variant(r.get("distribution") or {}, base_seed)
            if chosen:
                return chosen
            break

    return default_variant
"""
bu metot ise yukarıdaki metotları kullanarak geriye bir tane variant dönderir.Kod yapısına geçersek:
metot tanımlamasının içindeki ilk parametre olan * ifadesi verileri direkt bilgileri ile değil yani evaluate_one_flag(1,"key","off",rules,user) şeklinde geçirme,evaluate_one_flag(project_id=1,flag_key=" "....) şeklinde tanımla ki daha anlaşılır bir yapı
olsun diyor.diğer parametrelerimizde kullanacağımız parametrelerdir.
base_seed ifadesini oluştururken projenin id'si,flag id'si ve kullanıcının id'sine göre bir base_seed oluşturmak istedik ki,proje değiştiğin de veya flag değiştiğinde veya farklı bir kullanıcı geldiğinde farklı bucket değerleri oluşturulabilsin.Ayriyeten
sonuncu ifade de user dict'inden id bilgisi alınamazsa geri kalan user bilgilerini direkt string'e çevirip ver diyoruz.
sonrasında kurallarımızı tek tek geziyoruz.Hatırlarsak rules tablomuz içerisinde birden fazla kural olabileceğini ({"attr": "country", "op": "==", "value": "TR"} , {"attr": "is_premium", "op": "==", "value": True} gibi)  ve bu kurallarında birer id'ye 
sahip olacağından bahsetmiştik.bu yüzden bu kuralları tek tek dolaşıp uygun olan kurala göre variant atamasını yapacağız.
ilk olarak ilk id'ye sahip olan kuralı (kuralları öncelik sırasına göre yerleştiriyoruz db'ye) alıyoruz.sonrasında kullanıcının ilk kurala uyup uymadığını test etmek için _matches metotuna kullanıcıyı ve kuralların tutulduğu predicate bilgilerini 
yolluyoruz.eğer ki bu koşulu sağlarsa if içerisinde _pick_variant değişkenine varyantların yüzdelerini ve base_seed değişkenini yollayarak variant değerini alıyoruz,ardından bu dönen bilgiye göre chosen değişkeninin bir veriye sahip olup olmadığı kontrolunu
yani none olup olmadığı kontrolunu yapıyoruz,none değilse variant ismini geri dönderiyoruz,none ise break ile döngüden çıkarak varsayılan olarak belirlediğimiz variant'ı geriye dönderiyoruz.
küçük bir örnek:
parametre olarak geln bilgiler bunlar diyelim:
project_id = 1
flag_key = "enable_dark_mode"
default_variant = "off"
rules = [
    {
        "priority": 1,
        "predicate": {"attr": "country", "op": "==", "value": "TR"},
        "distribution": {"dark": 30, "off": 70}
    },
    {
        "priority": 2,
        "predicate": {"attr": "is_premium", "op": "==", "value": True},
        "distribution": {"dark": 80, "off": 20}
    },
]
user = {"country": "DE", "is_premium": True, "user_id": "u123"}

bu durumda base_seed=1:enable_dark_mode:u123 olur.ardından ilk if koşulunda ilk kurala bakılır ama ülke DE olduğu için ilk kurala uyulmaz ve ikinci kurala bakılır,ikinci kuralda is_premium şartını aradığı için ikinci kurala uyulur ve bu kural üzerinden
kodumuza devam ederiz ve gelen ifadelere göre de geriye bir varyant ismi dönderiririz.

"""
