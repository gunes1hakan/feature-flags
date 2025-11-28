from typing import Optional
from sqlmodel import SQLModel, Field
"""
bu class yapısı database'de project,environment ve sdkkey adında tablolarda işlem yapmamızı sağlar.
"""

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
"""
ürünün id'si ve ismi id ve name sütunlarında tutulmaktadır.
"""

class Environment(SQLModel, table=True):
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
swagger'da verilen name'in aynı olup olmadığı karşılaştırılıyor,eğer ki değer doğru ise code numarası 200 olacak şekilde bizi sonuçları yazacaktır.
"""