from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    DB_URL: str
    REDIS_URL: str 
    JWT_SECRET: str
    JWT_ALG: str 

    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

"""
    ---Settings sınıfının içine parametre olarak aldığı BaseSettings sınıfı aslında javada ki extends anlamına geliyor,peki bu sınıf ne yapıyor,bu sınıf veri doğrulama adımlarını
    kontrol etmektedir,örneğin str kısmı kendisine int türünden bir ifade geldiği zaman hata fırlatır gibi.Ayriyeten bu class yapısının OS'lardan gelen verilere göre oto olarak
    veri türünü ayarlayabilme özelliği vardır,bu yüzden BaseSettings sınıfını bu yapımızda kullandık.
    ---DB_URL,string türünden bir veri tutuyor ve de bu projede kullanılmasının sebebi ise environment(işletim sistemi değişkenlerinde) DB_URL adından herhangi bir değişken tanımlanmadıysa
    bunu kullan diyor ve de veritabanı bağlantı işlemlerini barındırıyor.
    ---Redis ifadesi bellekte hızlı işlem yapmamızı sağlar,normalde 10 defa db bağlantı işlemlerini yapacağız diyelim her seferinde disk üzerinden bilgi alıp vermek yerine direkt bellekten 
    bu bilgileri alarak daha hızlı işlem yapmamızı sağlar.burdaki kullanımı ise:
    redis ifadesi ise bu url redis için kullanılacaktır anlamına gelmektedir.6379 ifadesi port numarası iken 0 ise database'in numarasıdır.
    ilerde ise feature flag'den gelen işlemleri alıp rediste saklamak ve sdk'dan gelen istekleri hızlandırmak için kullanacağız.
    ---jwt_secret: ifadesinin açılımı json web token anlamına gelmektedir,Kullanıcı login olduğunda backend’in ürettiği imzalı token yapısı,Bu token, içinde kullanıcı id vs. taşır ve bir 
    gizli anahtarla imzalanır.İmza atarken de bu JWT_SECRET kullanılır.Şu anlık change me kullandık,ilerleyen zamanda bunu değiştireceğiz.
    ---JWT üretirken kullanılacak algoritmanın adını tutuyor."HS256" : HMAC-SHA256 algoritmasını ifade ediyor.Yaygın kullanılan simetrik imza yöntemi (aynı SECRET hem imzalar hem doğrular).
"""

settings = Settings()       #class isminin sonuna parantez koyulduğu zaman bu pythonda nesne oluştur anlamına gelmektedir,soldaki settings de bu nesneyi tutan bir referanstır.
