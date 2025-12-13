from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, UniqueConstraint
"""
bu class yapısı database'de project,environment ve sdkkey adında tablolarda işlem yapmamızı sağlar.
"""

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
"""
ürünün id'si ve ismi , id ve name sütunlarında tutulmaktadır.
"""

class Environment(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_env_project_name"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    project_id: int = Field(foreign_key="project.id", index=True)
    """
    bu tablo ise projenin ortamlarını yani (prod,dev) gibi ortamları tutmaktadır.
    tablo verileri id,name,project_id olarak tutmaktadır:
    örneğin project tablomda id ve name sütunları bulunmaktadır,bu id sütununun ilk elemanı 1 olsun ve tuttuğu name değeri de shop olsun,bu durumda bu ürünün project_id'si 1 olmaktadır.
    sonrasında bu ürünün farklı ortamlarını da environment tablosunda tutacağız,örnek vermek gerikirse:
    id:1   name:dev    project_id:1
    id:2   name:prod   project_id:1
    göründüğü gibi project_id'si 1 olan ürünün yani shop ürününün farklı ortamları için tablosu oluşturulmuş oldu.
    güncelleme: projeye ek olarak en üstte doğrulama adımı ekledik,uniqueConstraint adımı veritabanına normalde bu sütunda birden fazla aynı değere sahip ifadeye yer verme der,ama biz burda ekstra 
    olarak iki sütun girdik yani biri project_id,diğeri de name sütunudur.Yani veri tabanına daha önceden var olan project_id veya name alanına sahip olan bir eleman eklenecekse,db hata fırlat diyoruz.
    """

class SDKKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    environment_id: int = Field(foreign_key="environment.id", index=True)
    project_id: int = Field(foreign_key="project.id", index=True)
"""
bu class yapısı db'de sdkkey diye bir tane tablo ismi ile işlem yapar.
bu tabloda id,demo,environment_id ve project_id sütunları bulunmaktadır.
Her bir flag ürünü için bir tane özel keyimiz bulunmaktadır.(ör: demo,mobile gibi)
şimdi swagger'a gidip get kısmında yer alan env kısmına ortam ismimizi yazdıktan sonra sdk key kısmına da keyimizi yazdığımız zaman arka plan da şu dönüyor
öncelikle db de yer alan sdkkey tablomuzdaki yer alan key sütunlarına bakılıyor,eğer ki bizim swagger'da yazdığımız key ile uyuşuyorsa bize environment_id
ve project_id kısmını geri dönüyor,sonrasında ise yazılan environment tablosuna gidilip bakılıyor ve environment_id'nin yanındaki diğer sütundaki name ile
swagger'da verilen name'in aynı olup olmadığı karşılaştırılıyor,eğer ki değer doğru ise code numarası 200 olacak şekilde bize sonuçları yazacaktır.
Güncelleme: biz burda key değerini benzersiz olacak şekilde tanımlıyoruz,o zaman neden bu değeri tabloda primary key olarak oluşturmadık diye düşünebiliriz.
bunun sebebi key değerini ileri de değiştirebilmemizden dolayıdır,mesela ileri de key değeri demo3 olan keyi daha anlamlı olsun diye yarıkapalidemo3 diye
değiştirdim diyelim,bu durumda ben bu keyi primary key olarak tanımlarsam bu satırı silmem gerekecek ve bu durumda diğer tablolar ile olan ilişkisini de 
düzenlemem gerekecektir.ya da oldu da yanlışlıkla bu key değerini github'da paylaştık diyelim,bu durumda başkalarının bu key üzerinden yapacağı sorguları
engellemek amacıyla hızlıca bu key değerinin ismini değiştiririz ve hatayı ortadan kaldırmış oluruz.
"""

class FeatureFlag(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_flag_project_key"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True)               
    on: bool = True
    default_variant: str = "off"
    status: str = Field(default="draft", index=True)  # draft | active | published
    project_id: int = Field(foreign_key="project.id", index=True)
"""
-yukarıdaki kod yapısı db'de bulunan featureflag tablosu ile ilgilenmektedir.bu tabloda yer alan id kısmı primary key olarak ayarlanmış,
-key ise flag'imiz benzersiz bir keyi olacaktır.örnek vermek gerekirse biz bu uygulamamızda kullanıcıların karanlık tema özelliğini kullanabilmelerini yönetmek istiyoruz diyelim,bu örnek üzerinden ilerlersek key'imize 
uygulamamız ile uyumlu olacak şekilde "enable_dark_mode" ismini verebiliriz.
-on ise bu flag'imizin şu anda aktif olup olmadığını göstermektedir.
-default_variant ise kurallara uyulmadığında ya da özel bir dağıtım yoksa hangi varyant'ın kullanılacağını göstermektedir.bu default_variant'da off ifadesi varsayılanları kullan demektir ve de biz varsayılan olarak karanlık temayı kullanıcılara
kapattık,ama başka bir kullanım olan dark özelliğini de default_variant'a ekleyebiliriz,bu da karanlık tema modunu kullanıcıların kullanımına sunar.
-project_id ise bu flag'imizin hangi projeye ait olduğunu getirir.
-güncelleme:en üstteki kod yapısını zaten biliyoruz,ekstra olarak yapıtığımız projenin durumunu anlamak için status diye bir sütun ekledik,bu sütun draft,active,published diye değerleri tutuyoruz.varsayılan olarak draft değerini atıyoruz:
draft değeri yeni bir flag ekliyorum ama bu kodu halen yazıyorum,bu kod kullanıcıya gösterilmiyor ve başka kod yapıları tarafından çağrılmıyor,yani yapım aşamasında.
active değeri bir tane flag'in tamamlandığını kullanıcının kullanacabileceğini ama herhangi bir sıkıntı yaşanma durumuna karşı durumun sürekli izlendiğini belirtiyor.
published değeri ise artık bu flag'in final versiyonu olduğunu belirtir.
"""

class FeatureVariant(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("flag_id", "name", name="uq_variant_flag_name"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    flag_id: int = Field(foreign_key="featureflag.id", index=True)
    name: str                                   
    payload: dict = Field(default_factory=dict,sa_column=Column(JSON))
"""
bu class yapısında oluşturucağımız flag'in farklı varyantlarını oluşturuyoruz,örnek vermek gerekirse,yukarıdaki sınıfta karanlık temayı bir flag olarak seçelim demiştik,ama bu karanlık temanın bazı özel durumlara göre nasıl davranacağı hakkında
özel varyantlar tanımlayabiliriz.örnek vermek gerekirse:
varyant 1:soft dark,hafif gri tonlu olsun,bu sayede gözü de yormaz
varyant 2:tam siyah, oled ekranlarda pil tasarrufunu sağlar
varyant 3:blue dark, daha mavi tonlu,markaya uygun olarak tasarlanmış karanlık tema
-Kodun içine geçersek:
-id:her varyantın kendine ait benzersiz id'sinin olmasını sağladık.
-flag_id: featureflag tablosundan bilgiye alarak hangi flag'e bağlı olduğunu buluyoruz.
-name: varyantın adını tanımlamaktadır,örneğin yukarıda örnek olarak verdiğimiz soft dark gibi
-payload kısmında yer alan dict ise bilgilerimizi key value cinsinden json verisi şeklinde tutmaktadır.bu veri türüne örnek vermek gerekirse theme:dark,bu şekilde varyantımızın ne olduğunu key value şeklinde vermiş oluyoruz.
ayriyeten bu dict içerisinde default_factory=dict kısmı ile diyoruz ki featuevariant tablosunda yeni satır eklendiği zaman ve payload kısmı doldurulmadığı zaman bu payload kısmına boş bir değer ata,bu şekilde none hatası ile de uğraşmamaış oluyoruz
sa_column=Column(JSON) bu kod yapısı ise sqlalchemy'nin özelliğidir.bu kod satırı payload alanının veritabaınnda json şeklinde veri tutacağını anlatmaktadır.
"""

class FeatureRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flag_id: int = Field(foreign_key="featureflag.id", index=True)
    environment_id: int = Field(foreign_key="environment.id", index=True)
    priority: int = 1
    predicate: dict = Field(default_factory=dict, sa_column=Column(JSON))
    distribution: dict = Field(default_factory=dict, sa_column=Column(JSON))
"""
-bu class yapısı bize kurallara uyan kullanıcılara nasıl dağıtım yapacağımız hakkında bilgi vermektedir.
-id:her kuralın benzersiz bir id'si bulunur.
-flag_id:bu kural hangi flag'e uygulanacak bilgisini tutar.
-environment_id: bu kuralın hangi ortam için oluşturulduğu bilgisini tutmaktadır.(ör:prod,dev)
-priority:aynı flag için birden fazla kuralımız bulunacağından ilk önce hangi kuraldan başlayarak karşılaştırma işlemi yapılacağını bildiyoruz,yani kısaca karşılaştırma işlemine 1. kuraldan başla diyoruz.
-predicate:oluşturulan kuralın hangi kullanıcılar için geçerli olduğu bilgisini tutmaktadır,örnek vermek gerekirse featurerule tablosundaki predicate sütununda verilerimiz {"attr": "country", "op": "==", "value": "TR"} şeklinde tutuluyor.bu veri
şunu demek istiyor,ülkesi TR olan kullanıcılar bu kurala uysun.
-distribution: bu kod yapısı ise predicate'de yer alan kurallara uyan kullanıcılara özellikleri hangi oranda vereyim bilgilerini tutar.
Bu kısmı da daha açıklayıcı şekilde anlatmak için,featurerule tablosundan kısa bir örnek vermek gerekirse:
id: 1  flag_id:10  environment_id:3  priority:1  predicate:{"attr": "country", "op": "==", "value": "TR"}  distrubition: {"dark": 30, "off": 70}
id: 2  flag_id:10  environment_id:3  priority:2  predicate:{"attr": "country", "op": "==", "value": "DE"}  distrubition: {"dark": 10, "off": 90}
id: 3  flag_id:10  environment_id:3  priority:3  predicate:{"attr": "is_premium", "op": "==", "value": true}  distrubtion: {"dark": 80, "off": 20}
mesela {"country": "TR", "age": 25} diye bir tane user data'mız var diyelim,predicate ksımı gidip bu data'nın içerisindeki country seçeneğine bakar ve TR ile eşit mi kontrolunu yapar,kurala uyduğu için priority numarası 1 olan kısım bu kullanıcıya
uygulanır.
"""