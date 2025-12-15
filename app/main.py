from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.db import init_db
from app.routers import sdk, admin

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

app.include_router(admin.router, prefix="/admin/v1", tags=["admin"])    #admin router'ı bağlandı.

app.include_router(sdk.router, prefix="/sdk/v1", tags=["sdk"])
"""
SDK router'ı bağlama
Ayrı bir dosyada tanımladığın sdk router’ını ana uygulamaya bağlıyor.
Bu sayede:
/sdk/v1/flags gibi endpoint’ler aktif oluyor.
Swagger’da “sdk” diye ayrı bir grup altında görünüyor.
Özet: “Feature flags’i dış dünyaya servis eden asıl endpoint’leri” bu satır projeye ekliyor.
"""