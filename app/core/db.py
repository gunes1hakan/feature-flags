from sqlmodel import SQLModel, create_engine, Session
from app.core.settings import settings

engine = create_engine(     #mysql bağlantısı yapmak için bize gerekli olan nesneyi dönderir.
    settings.DB_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600
)

def get_session():     
    with Session(engine) as session:
        yield session
"""" 
Session(engine) ile bir obje oluşturdum ve bu objemi de as yanında bulunan session referansına atadım,sonrasında bu referans ile işlem yaptım,yani farklı bir class içerisinde session.add() 
gibi veri tabanı işlemlerimi yaptım diyelim bir endpoint için sonrasında ise bu endpointle işim bittiğimde bu with ifadesi bu oluşturduğu session adlı nesneyi öldürüyor.
yield ifadesi ise geriye nesne dönderiyordu,böylece yield ifadesinden önceki kısımlar hazırlık sonraki kısımda ise işim bittiğinde nesneyi öldürmüş oluyoruz.
"""


def init_db():
    SQLModel.metadata.create_all(engine)
"""
4️⃣ init_db() fonksiyonu nedir?

Kod:

def init_db():
    SQLModel.metadata.create_all(engine)

4.1 SQLModel burada ne işe yarıyor?

SQLModel:

from sqlmodel import SQLModel ile gelen sınıf.

Bizim kendi modellerimiz (mesela Project) bundan miras alıyor:

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


SQLModel sınıfının içinde bir de metadata denen bir şey var:

SQLModel.metadata


Bu metadata, bu sınıftan türeyen tüm tablo tanımlarını içinde tutuyor:

Project tablosu,

İleride ekleyeceğin başka modeller,

Hepsini bir arada saklayan bir “schema koleksiyonu”.

4.2 create_all(engine) ne yapıyor?
SQLModel.metadata.create_all(engine)


Bu ifade:

“Elimdeki tüm tablo tanımlarına bak,
eğer bunlar veritabanında yoksa, oluştur.”

Yani:

SQLModel.metadata → hangi tablolar var, kolonları neler, tipleri neler → hepsini biliyor.

.create_all(engine) → bu şemaya bakıyor, MySQL’e gidiyor ve:

CREATE TABLE project (...) gibi SQL komutları çalıştırıyor.

Bu işlemi genelde:

Uygulama ilk ayağa kalkarken bir kere yapıyoruz.

Nitekim main.py içinde:

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # create tables if not exist
    yield


dediğin için, FastAPI uygulaması başlarken:

init_db() çağrılıyor,

SQLModel’den türeyen tüm modellerin tabloları (örneğin Project) veritabanında oluşturuluyor (yoksa).

Özetle:

init_db → “veritabanı şemasını başlat” fonksiyonu.

SQLModel → tüm modellerin kök sınıfı.

.metadata.create_all(engine) → modellerine göre CREATE TABLE komutlarını çalıştırır.
"""