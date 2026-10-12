# belediye-demo-gen notları

## 2026-08-31 — ilk sürüm
- Bahçelievler Belediyesi için `bld_bahcelievler` üretildi.
- Şema `erp-demo-gen`den bağımsız; ortak olan tek şey `erp_demo_pg` konteyneri.
- Yükleme `docker exec -i ... psql -c "\copy ... FROM STDIN"` ile yapılıyor;
  `erp-demo-gen`in `./out:/data` mount'una bağımlı değil.
- Tarih aralığı 2019-01-01 .. 2026-08-31; `engine/util.py` içinde `BASLANGIC`
  ve `BITIS` sabitleri.
