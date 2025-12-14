from typing import Any, Dict, List
from pydantic import BaseModel, Field
"""
bu dosya yapım istemcinin API'ye hangi formatta veri göndereceğini,API'nin istemciye hangi formatta veri göndereceği gibi bilgileri taşımaktadır.
peki bu dosya yapım neden var,eğer ki biz bu sınıfı kullanmazsak ve verileri direkt db'den dönderirsek dönderdiğimiz API'de project_id ya sdk key id
gibi hem güvenlik acısından riskli hem de gereksiz bilgileri API ile yollayacaktı.Başka bir durumda ise şöyle bir sıkıntı oluşurdu,eğer ki db'den direkt
veri çekilecekse ve ilerde db'ye yeni sütunlar eklenecekse bu veri tutarsızlığı doğuracaktı.bunu engellemek için db'deki tüm verileri değil de bazı verileri
geri döndermek için schemas adlı dosya yapısını oluşturduk.
pydantic python'un schema tanımlaması yapan özel bir kütüphaensidir.
"""

class FeatureRuleOut(BaseModel):
    priority: int
    predicate: Dict[str, Any]
    distribution: Dict[str, float]
"""
kuralları belli bir formata sokmak için tasarlanmış bir class yapısıdır,normalde bu kurallar /sdk/v1/flags endpointinde sdk.py dosyasının dönderdiği cinsten veriler içerirken
artık yukarıdaki bilgilere uyacak şekilde bilgiyi geriye çevirecek.(şimdilik aslında yine aynı verileri dönderiyorlar,ama arada distribution dict'inin value değerinin float olması
gibi çok küçük değişiklikler bulunmaktadır.)
"""

class FeatureFlagOut(BaseModel):
    key: str
    on: bool
    default_variant: str
    variants: Dict[str, Dict[str, Any]]
    rules: List[FeatureRuleOut]
    configs: Dict[str, Any] = Field(default_factory=dict)

class FlagsResponse(BaseModel):
    env: str
    project_id: int
    flags: List[FeatureFlagOut]
#FeatureFlagOut class'ı /sdk/v1/flags endpointinin içindeki Flags nesnesini düzenlerken,FlagsResponse class'ı ise komple /sdk/v1/flags endpointini düzenler.

class EvaluateUserIn(BaseModel):
    user: Dict[str, Any]
#bu class POST /sdk/v1/evaluate endpointinin request body'den yani gelen veriyi düzenler.

class EvaluateResponse(BaseModel):
    env: str
    project_id: int
    variants: Dict[str, str]
#bu class ise POST /sdk/v1/evaluate endpointinin döndüğü veriyi düzenler.
