# Redis Cache Verify (Feature Flags)

## 0) Stack ayakta mı?
docker compose ps

## 1) API container Redis env kontrolü
docker exec -it ff-api env | findstr REDIS

## 2) Redis ping
docker exec -it ff-redis redis-cli ping

## 3) Cache key tarama
docker exec -it ff-redis redis-cli --scan --pattern "ff:flags:*"

## 4) Örnek key TTL ve GET (ör: ff:flags:2:2)
docker exec -it ff-redis redis-cli ttl ff:flags:2:2
docker exec -it ff-redis redis-cli get ff:flags:2:2

## 5) (Opsiyonel) Monitor ile cache hit görmek
docker exec -it ff-redis redis-cli monitor
