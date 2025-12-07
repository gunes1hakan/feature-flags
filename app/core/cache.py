# app/core/cache.py
import json
from typing import Any, Optional
from redis.asyncio import Redis
from redis import Redis as RedisSync
from app.core.settings import settings
"""
normalde /sdk/v1/flags endpoint'i şunu yapar:
-Env+SDK key alıyor,DB'den flag+variant+rule bilgilerini çekiyor ve bunları tek bir json olarak dönderiyor.
-ama yukarıdaki işlem çok iş yükü barındırıyor,her bir istek için db'ye 3-4 sorgu atılıyor.
-işte yukardaki iş yükünü azaltmak için cache katmanını ekledik,bu katman /sdk/v1/flags endpointi çalıştığında ilk olarak DB'den bilgileri normal topluyor,sonrasında ise Redis'e kaydediyor.bu sayede yeni sorgular atıldığında 
DB'ye gidilmiyor,yalnızca Redis'ten hazır JSON'u çekiliyor.
""" 

_redis: Optional[Redis] = None
"""
burda global bir değişken olarak _redis oluşturduk çünkü aşağıdaki metotların her birinde tek tek Redis.from_url() demekle uğraşmayalım diye.
değerini aşağıdaki _get_client() metotundan alacak.
"""

async def _get_client() -> Optional[Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis
"""
-bu metot bir client oluşturur.Yapısı ise:
global _redis ile dışardaki _redis'i kullanacağım dedikten sonra ilk if koşuluna giriyorum,burda _redis'in boş olup olmama durumunu kontrol ediyorum,eğer ki boş ise if bloğuna giriyorum ve 
try bloğunun içerisinde _redis'i oluşturuyorum.(redis oluşturma sırasında from_url metotu içerisindeki ilk parametre .env'nin kendi bağlantısından gelirken,ikinci parametresi ise bilgilerin byte olark değil de string olarak tutulacağından bahsediyor.)
bağlantı url'sini oluşturduktan sonra sunucu ile gerçekten bağlantı kurup kurmadığını test etmek için ping() meottunu kullanıyoruz,eğer ki url yanlışsa veya redis kapalıysa gibi durumlar oluştuğunda bir hata fırlatıyor.
bu hata bloğunun içerisinde de _redis'i tekrardan none olarak değiştiriyoruz.
son olarak ise bu _redis'i geri dönderiyoruz.
"""

async def cache_get_json(key: str):
    client = await _get_client()
    if not client:
        return None
    try:
        raw = await client.get(key)
        return None if raw is None else json.loads(raw)
    except Exception:
        return None
"""
sdk.py içerisinden bu metota parametre olarak bir tane key yollanıyor.ardından bu metot içerisine girdiğimizde:
-ilk olarak yukarıdaki _get_client() metotundan alınan client değeri client değişkenine atanıyor.
-ardından ilk if koşulunda eğer ki bu client boş ise none değeri dönderiliyor,değilse try bloğuna giriyor ve raw değişkenine verilen key değeri ile client'dan alınan("{"env": "prod", "flags": [...]}" gibi) json verisi atanıyor.
ardından altındaki return ile bir if kontrolu yapılır raw is None ise geriye None değeri dönderilirken None değilse veri Python objesine(dict) çevrilerek geri dönderilir.
-eğer ki bir hata meydana gelirse herhangi bir sıkıntı yaşanmaması adına cache yokmuş gibi davranması için none değerini geri dönderiyoruz.
"""    

async def cache_set_json(key: str, value: Any, ttl_seconds: int = 120):
    client = await _get_client()
    if not client:
        return
    try:
        await client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        pass
"""
bu metot kısaca DB'den toplanılan verileri 120 saniye boyunca rediste saklar.metotun içeriğine geçersek:
-bu metot içerisinde işlem yapabilmememiz için öncelikle parametre olarak bir Redis anahtarı,ardından json'a dönüştürüp kaydedeceğimiz bir Python objesi(dict,list vs.) ve verilerin cache'de kaç saniye kalacağı bilgilerini tutuyourz.
-öncelikle client değerini alıyoruz.
-client boş ise return ile metottan çıkıyoruz.
-değilse try bloğu içerisinde setex komutu ile diyoruz ki,key ismiyle,120 sn kadar süreyle,JSON string olarak kaydet.
-eğer ki bir hata fırlarsa hiçbir şey yapmadan devam et diyoruz.
"""    

def invalidate_project_sync(project_id: int):
    try:
        r = RedisSync.from_url(settings.REDIS_URL, decode_responses=True)
        for k in r.scan_iter(match=f"ff:flags:{project_id}:*"):
            r.delete(k)
    except Exception:
        pass
"""
-bu metotumuzda admin herhangi bir güncelleme işlemi veya silme işlemi gibi bir işlem yaptığında kullanıcılar bu değişiklikleri 120 sn gibi bir süre sonra görmesinler yani direkt yapılan dğişiklikleri görsünler diye yapılan bir metottur.
-öncelikle bu metotumuz diğer metotlar gibi async çalışmıyor sync çalışıyor çünkü main dosyası içerisinde endpointleri çağrıları sync şeklinde olmaktadır.
-arından kod yapımıza giriyoruz,r değişkenine normal(senkron) redis client'ımızı atıyoruz
-ardından bir for döngüsü ile ff:flags:{project_id}:* keyine uyan tüm keyleri getiriyoruz.
-sonrada bu keyleri cache'den siliyoruz.
-eğer ki bir hata kalırsa hiçbir şey yapmadan geç diyoruz(zaten bir cache'nin ömrü 120 sn olduğu için geç de olsa bu bilgiler farklı yerlerde görünecektir.)
"""  
