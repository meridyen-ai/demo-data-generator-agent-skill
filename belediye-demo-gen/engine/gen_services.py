# -*- coding: utf-8 -*-
"""Imar, zabita, fen isleri, filo, temizlik ve cevre hizmetleri."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

PARK_ADLARI = ["Cumhuriyet", "Barış", "Şehit Er", "Zafer", "15 Temmuz Şehitler",
               "Fatih", "Çamlık", "Gül", "Papatya", "Menekşe", "Yeşilvadi",
               "Dostluk", "Sevgi", "Çocuk", "Emek", "Bahar", "Hürriyet", "Anadolu",
               "Karanfil", "Lale", "Ihlamur", "Çınaraltı", "Adalet", "Kardeşlik",
               "Umut", "Güneş", "Yıldız", "Nilüfer", "Fidanlık", "Söğütlü"]

ARAC_SINIF = [
    ("Çöp kamyonu", 46, "Motorin", ("Temizlik İşleri Müdürlüğü",)),
    ("Süpürge aracı", 14, "Motorin", ("Temizlik İşleri Müdürlüğü",)),
    ("Kamyon", 28, "Motorin", ("Fen İşleri Müdürlüğü", "Park ve Bahçeler Müdürlüğü")),
    ("Kamyonet", 52, "Motorin", ("Fen İşleri Müdürlüğü", "Park ve Bahçeler Müdürlüğü",
                                  "Destek Hizmetleri Müdürlüğü", "Zabıta Müdürlüğü")),
    ("Binek", 62, "Benzin", ("Destek Hizmetleri Müdürlüğü", "Zabıta Müdürlüğü",
                              "İmar ve Şehircilik Müdürlüğü", "Sosyal Yardım İşleri Müdürlüğü")),
    ("Minibüs", 24, "Motorin", ("Kültür ve Sosyal İşler Müdürlüğü",
                                 "Gençlik ve Spor Hizmetleri Müdürlüğü")),
    ("İş makinesi", 22, "Motorin", ("Fen İşleri Müdürlüğü",)),
    ("Vinç", 6, "Motorin", ("Fen İşleri Müdürlüğü",)),
    ("Arazöz", 8, "Motorin", ("Park ve Bahçeler Müdürlüğü",)),
    ("Cenaze aracı", 7, "Motorin", ("Sağlık İşleri Müdürlüğü",)),
    ("Ambulans", 4, "Motorin", ("Sağlık İşleri Müdürlüğü",)),
]

MARKALAR = ["Ford", "Mercedes-Benz", "Iveco", "BMC", "Isuzu", "Volkswagen", "Fiat",
            "Renault", "Hyundai", "Toyota", "MAN", "JCB", "Hidromek", "Caterpillar"]

ISTASYONLAR = [("Bahçelievler Hava Kalitesi İstasyonu", 1),
               ("Yenibosna İstasyonu", 10),
               ("Şirinevler İstasyonu", 9),
               ("Kocasinan İstasyonu", 6)]


def uret(w):
    d = w.depo
    rng = w.r("services")
    mud = w.mud_by_ad

    # ============================================================ IMAR
    zid, pid_, oid_ = 0, 0, 0
    w.imar_basvuru = []
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        adet = int(2150 * gun_orani * rng.uniform(0.88, 1.14))
        for _ in range(adet):
            zid += 1
            tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            tur = U.agirlikli(rng, [("İmar durumu belgesi", 32), ("Yeni yapı ruhsatı", 14),
                                    ("Tadilat ruhsatı", 13), ("Plan tadilatı", 6),
                                    ("İfraz-tevhid", 7), ("Kot kesit", 9),
                                    ("Yapı kayıt belgesi", 11), ("Yıkım ruhsatı", 8)])
            bina = rng.choice(w.binalar)
            durum = U.agirlikli(rng, [("Onaylandı", 68), ("Reddedildi", 11),
                                      ("Eksik evrak", 10), ("İncelemede", 7), ("İptal", 4)])
            sure = U.normal_int(rng, 26, 22, 1, 240)
            sonuc = tarih + dt.timedelta(days=sure) if durum not in ("İncelemede",) else None
            harc = 0.0
            if durum == "Onaylandı":
                harc = {"İmar durumu belgesi": 480, "Yeni yapı ruhsatı": 14500,
                        "Tadilat ruhsatı": 4200, "Plan tadilatı": 9800,
                        "İfraz-tevhid": 3100, "Kot kesit": 620,
                        "Yapı kayıt belgesi": 2400, "Yıkım ruhsatı": 1800}[tur] \
                    * w.endeks(tarih) * rng.uniform(0.7, 2.2)
            d.w(T.zoning_application).yaz(
                zoning_application_id=zid, application_no=f"İM-{yil}-{zid:06d}",
                application_date=tarih, application_type=tur,
                neighborhood_id=bina["mah"], building_id=bina["id"],
                parcel_no=f"{rng.randrange(100, 3200)}/{rng.randrange(1, 60)}",
                applicant_citizen_id=rng.choice(w.vat_by_mah[bina["mah"]]),
                applicant_type=U.agirlikli(rng, [("Malik", 54), ("Müteahhit", 27),
                                                 ("Vekil", 15), ("Kamu kurumu", 4)]),
                result_date=sonuc, status=durum, processing_days=sure,
                fee_amount=U.para(harc),
                rejection_reason=None if durum != "Reddedildi" else U.agirlikli(
                    rng, [("İmar planına aykırı", 34), ("Emsal aşımı", 22),
                          ("Eksik proje", 20), ("Komşu parsel muvafakati yok", 12),
                          ("Tapu kaydı uyuşmuyor", 12)]))
            # ruhsat
            if durum == "Onaylandı" and tur in ("Yeni yapı ruhsatı", "Tadilat ruhsatı") and sonuc:
                pid_ += 1
                kat = U.normal_int(rng, 6, 2, 2, 16)
                bb = kat * U.agirlikli(rng, [(2, 30), (3, 28), (4, 30), (6, 12)])
                alan = bb * rng.uniform(85, 140)
                d.w(T.building_permit).yaz(
                    building_permit_id=pid_, zoning_application_id=zid,
                    permit_no=f"YR-{yil}-{pid_:05d}", issue_date=sonuc,
                    neighborhood_id=bina["mah"], building_id=bina["id"],
                    permit_type="Yeni yapı" if tur == "Yeni yapı ruhsatı" else U.agirlikli(
                        rng, [("Tadilat", 62), ("İlave", 20), ("Yenileme", 12),
                              ("İsim değişikliği", 6)]),
                    usage_class=U.agirlikli(rng, [("Konut", 72), ("Karma", 16),
                                                  ("Ticari", 8), ("Eğitim", 2),
                                                  ("Sağlık", 1), ("Sanayi", 1)]),
                    floor_count=kat, unit_count=bb, construction_area_m2=round(alan, 2),
                    contractor_name=U.firma_adi(rng),
                    estimated_cost=U.para(alan * 26000 / w.endeks(2026) * w.endeks(sonuc)),
                    permit_fee=U.para(harc),
                    status=U.agirlikli(rng, [("İskan alındı", 46), ("Geçerli", 34),
                                             ("Süresi doldu", 14), ("İptal edildi", 6)]))
                # iskan
                if rng.random() < 0.52:
                    ay_gecen = U.normal_int(rng, 26, 10, 6, 60)
                    iskan_gun = sonuc + dt.timedelta(days=ay_gecen * 30)
                    if iskan_gun <= U.BITIS:
                        oid_ += 1
                        d.w(T.occupancy_permit).yaz(
                            occupancy_permit_id=oid_, building_permit_id=pid_,
                            permit_no=f"YKİ-{iskan_gun.year}-{oid_:05d}",
                            issue_date=iskan_gun, neighborhood_id=bina["mah"],
                            building_id=bina["id"], unit_count=bb,
                            construction_area_m2=round(alan, 2),
                            fee_amount=U.para(alan * 42 / w.endeks(2026) * w.endeks(iskan_gun)),
                            elapsed_months_from_permit=ay_gecen)

    # ================================================== deprem risk tespiti
    sid = 0
    firmalar = ["Anadolu Yapı Denetim A.Ş.", "Marmara Teknik Müşavirlik Ltd. Şti.",
                "Kale Yapı Laboratuvarı A.Ş.", "Zemin Etüt Mühendislik Ltd. Şti.",
                "Boğaziçi Yapı Denetim Ltd. Şti."]
    for b in w.binalar:
        if b["risk"] == "Düşük" and rng.random() > 0.06:
            continue
        if b["risk"] == "Orta" and rng.random() > 0.22:
            continue
        if rng.random() > 0.72:
            continue
        sid += 1
        gun = U.rastgele_gun(rng)
        riskli = b["risk"] in ("Yüksek", "Acil riskli")
        sonuc = ("Riskli" if riskli and rng.random() < 0.78 else
                 U.agirlikli(rng, [("Risksiz", 54), ("Güçlendirme önerildi", 30),
                                   ("Veri yetersiz", 16)]))
        yikim = None
        if sonuc == "Riskli" and b["donusum"] in ("Yıkıldı", "Yeniden yapıldı"):
            yikim = min(U.BITIS, gun + dt.timedelta(days=rng.randrange(120, 900)))
        kira_yardim = sonuc == "Riskli" and rng.random() < 0.62
        d.w(T.earthquake_risk_survey).yaz(
            earthquake_risk_survey_id=sid, building_id=b["id"], neighborhood_id=b["mah"],
            survey_date=gun, survey_firm=rng.choice(firmalar), risk_result=sonuc,
            concrete_strength_mpa=round(rng.uniform(7, 32), 2),
            rebar_condition=U.agirlikli(rng, [("İyi", 38), ("Orta", 42), ("Kötü", 20)]),
            recommended_action=("Yıkım" if sonuc == "Riskli" else
                                "Güçlendirme" if sonuc == "Güçlendirme önerildi" else
                                "Detaylı inceleme" if sonuc == "Veri yetersiz" else "İşlem yok"),
            demolition_date=yikim, rental_aid_granted=kira_yardim,
            rental_aid_amount=U.para(9500 * w.endeks(gun) * rng.uniform(10, 22)
                                     if kira_yardim else 0))

    # ============================================================ ZABITA
    zabita = [p["id"] for p in w.personeller
              if p["unvan"]["ad"] in ("Zabıta Memuru", "Zabıta Komiseri", "Zabıta Amiri")]
    isyeri_by_mah = {}
    for b in w.isyerleri:
        isyeri_by_mah.setdefault(b["mah"], []).append(b["id"])
    aid, cid = 0, 0
    for gun in U.gunler():
        gunluk = U.normal_int(rng, 26, 8, 4, 70)
        if gun.weekday() >= 5:
            gunluk = int(gunluk * 0.62)
        for _ in range(gunluk):
            aid += 1
            m = U.agirlikli(rng, [(mm["id"], mm["nufus2026"]) for mm in w.mahalleler])
            tur = U.agirlikli(rng, [("Seyyar satıcı müdahalesi", 17), ("İşgaliye denetimi", 15),
                                    ("Pazar denetimi", 12), ("Gürültü şikayeti", 11),
                                    ("İnşaat çevre düzeni", 9), ("Etiket denetimi", 8),
                                    ("Kaldırım işgali", 12), ("Hafriyat denetimi", 6),
                                    ("Dilencilik", 4), ("İlan ve reklam denetimi", 6)])
            sonuc = U.agirlikli(rng, [("Uyarı", 42), ("Tutanak düzenlendi", 22),
                                      ("İdari para cezası", 17), ("Malzeme el konuldu", 9),
                                      ("İşlem yapılmadı", 8), ("Faaliyetten men", 2)])
            d.w(T.municipal_police_action).yaz(
                municipal_police_action_id=aid, action_date=gun, neighborhood_id=m,
                action_type=tur,
                source=U.agirlikli(rng, [("Rutin devriye", 44), ("Vatandaş ihbarı", 31),
                                         ("CİMER", 9), ("Muhtar bildirimi", 8),
                                         ("Kurum içi", 8)]),
                team_code=f"ZE-{rng.randrange(1, 19):02d}",
                employee_id=rng.choice(zabita) if zabita else None,
                result=sonuc, response_minutes=U.normal_int(rng, 42, 30, 5, 300),
                seized_item_count=rng.randrange(1, 60) if sonuc == "Malzeme el konuldu" else 0)
            if sonuc in ("İdari para cezası", "Faaliyetten men") or rng.random() < 0.04:
                cid += 1
                dayanak = U.agirlikli(rng, [("1608 sayılı Kanun", 34),
                                            ("5326 Kabahatler Kanunu", 30),
                                            ("3194 İmar Kanunu", 16),
                                            ("2872 Çevre Kanunu", 12),
                                            ("1593 Umumi Hıfzıssıhha", 8)])
                tutar = 2200 * w.endeks(gun) * rng.uniform(0.4, 9.0)
                r = rng.random()
                cdurum = ("Tahsil edildi" if r < 0.52 else "Ödenmedi" if r < 0.74
                          else "İtiraz edildi" if r < 0.85
                          else "İcraya verildi" if r < 0.95 else "İptal edildi")
                indirimli = tutar * 0.75
                tahsil = (indirimli if cdurum == "Tahsil edildi" and rng.random() < 0.7
                          else tutar if cdurum == "Tahsil edildi" else 0.0)
                havuz = isyeri_by_mah.get(m) or [None]
                isyeri = rng.choice(havuz)
                d.w(T.penalty_decision).yaz(
                    penalty_decision_id=cid, municipal_police_action_id=aid,
                    decision_date=gun, neighborhood_id=m,
                    business_id=isyeri if rng.random() < 0.7 else None,
                    citizen_id=rng.choice(w.vat_by_mah[m]) if rng.random() < 0.4 else None,
                    legal_basis=dayanak, violation_type=tur,
                    penalty_amount=U.para(tutar), discounted_amount=U.para(indirimli),
                    collected_amount=U.para(tahsil),
                    payment_date=(gun + dt.timedelta(days=rng.randrange(1, 90))
                                  if tahsil > 0 else None),
                    status=cdurum)

    # ============================================== FEN ISLERI / ALTYAPI
    # parklar
    prid = 0
    w.parklar = []
    for m in w.mahalleler:
        adet = U.normal_int(rng, int(m["alan"] * 11), 4, 6, 34)
        for i in range(adet):
            prid += 1
            tur = U.agirlikli(rng, [("Mahalle parkı", 34), ("Cep parkı", 26),
                                    ("Çocuk oyun alanı", 22), ("Semt bahçesi", 9),
                                    ("Spor alanı", 7), ("Koru", 2)])
            alan = {"Mahalle parkı": rng.uniform(1200, 9000), "Cep parkı": rng.uniform(180, 900),
                    "Çocuk oyun alanı": rng.uniform(300, 1600),
                    "Semt bahçesi": rng.uniform(4000, 22000),
                    "Spor alanı": rng.uniform(800, 5000),
                    "Koru": rng.uniform(12000, 48000)}[tur]
            yil = rng.randrange(1994, 2027)
            d.w(T.park).yaz(
                park_id=prid, park_name=f"{rng.choice(PARK_ADLARI)} Parkı",
                neighborhood_id=m["id"], park_type=tur, area_m2=round(alan, 2),
                opening_year=yil,
                playground_count=rng.randrange(0, 4), fitness_equipment_count=rng.randrange(0, 14),
                has_wc=alan > 2500 and rng.random() < 0.7,
                has_cafe=alan > 5000 and rng.random() < 0.45,
                irrigation_type=U.agirlikli(rng, [("Otomatik", 42), ("Damlama", 26),
                                                  ("Manuel", 26), ("Yok", 6)]),
                annual_maintenance_cost=U.para(alan * 78 * w.endeks(2025) * rng.uniform(0.6, 1.6)),
                tree_count=int(alan / rng.uniform(22, 60)),
                accessibility_score=U.normal_int(rng, 68 if yil >= 2012 else 44, 18, 5, 100))
            w.parklar.append(prid)

    # yol calismalari
    rid = 0
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        adet = int(430 * ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0 * rng.uniform(0.85, 1.2))
        for _ in range(adet):
            rid += 1
            sok, m = w.sokaklar[rng.randrange(len(w.sokaklar))]
            tur = U.agirlikli(rng, [("Sıcak asfalt", 22), ("Yama", 30), ("Parke taşı", 14),
                                    ("Kaldırım yenileme", 18), ("Bordür", 8),
                                    ("Yağmur suyu ızgara", 5), ("Hemzemin düzenleme", 3)])
            bas = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            sure = rng.randrange(1, 45)
            alan = {"Sıcak asfalt": rng.uniform(600, 9000), "Yama": rng.uniform(30, 400),
                    "Parke taşı": rng.uniform(200, 2600),
                    "Kaldırım yenileme": rng.uniform(120, 2200),
                    "Bordür": rng.uniform(60, 900), "Yağmur suyu ızgara": rng.uniform(10, 120),
                    "Hemzemin düzenleme": rng.uniform(200, 1800)}[tur]
            asfalt = alan * 0.13 if tur in ("Sıcak asfalt", "Yama") else 0.0
            maliyet = alan * 640 / w.endeks(2026) * w.endeks(bas) * rng.uniform(0.7, 1.5)
            bitis = bas + dt.timedelta(days=sure)
            soz = [s for s in w.sozlesmeler if s["mud"] == mud["Fen İşleri Müdürlüğü"]
                   and s["bas"] <= bas <= s["bit"]]
            d.w(T.road_work).yaz(
                road_work_id=rid, street_id=sok, neighborhood_id=m, work_type=tur,
                start_date=bas, end_date=bitis if bitis <= U.BITIS else None,
                area_m2=round(alan, 2), asphalt_ton=round(asfalt, 2),
                cost_amount=U.para(maliyet),
                contract_id=rng.choice(soz)["id"] if soz and rng.random() < 0.5 else None,
                executed_by=U.agirlikli(rng, [("Yüklenici", 62), ("Belediye ekibi", 38)]),
                status=("Tamamlandı" if bitis <= U.BITIS else "Devam ediyor"))

    # sokak aydinlatma
    lid = 0
    for m in w.mahalleler:
        adet = int(m["nufus2026"] / 68)
        for _ in range(adet):
            lid += 1
            montaj = U.rastgele_gun(rng, dt.date(2005, 1, 1), U.BITIS)
            tip = ("LED" if montaj.year >= 2018 else U.agirlikli(
                rng, [("Sodyum buharlı", 52), ("LED", 22), ("Cıva buharlı", 18),
                      ("Metal halide", 8)]))
            guc = {"LED": rng.choice([60, 80, 100, 120]),
                   "Sodyum buharlı": rng.choice([150, 250]),
                   "Cıva buharlı": rng.choice([125, 250]),
                   "Metal halide": rng.choice([150, 250])}[tip]
            d.w(T.street_light).yaz(
                street_light_id=lid, street_id=rng.choice(w.sokak_by_mah[m["id"]]),
                neighborhood_id=m["id"], lamp_type=tip, power_watt=guc,
                install_date=montaj,
                last_maintenance_date=U.rastgele_gun(rng, max(montaj, U.BASLANGIC), U.BITIS),
                status=U.agirlikli(rng, [("Çalışıyor", 92), ("Arızalı", 5),
                                         ("Bakımda", 2), ("Söküldü", 1)]),
                annual_kwh=round(guc * 4100 / 1000.0, 2))

    # altyapi arizalari
    fid = 0
    for gun in U.gunler():
        adet = U.normal_int(rng, 11, 5, 0, 40)
        if gun.month in (11, 12, 1, 2):
            adet = int(adet * 1.35)
        for _ in range(adet):
            fid += 1
            m = U.agirlikli(rng, [(mm["id"], mm["nufus2026"]) for mm in w.mahalleler])
            tur = U.agirlikli(rng, [("Sokak lambası arızası", 31), ("Yol çökmesi", 8),
                                    ("Rögar kapağı", 11), ("Yağmur suyu tıkanıklığı", 16),
                                    ("Devrilen ağaç", 7), ("Kaldırım hasarı", 15),
                                    ("Trafik levhası", 7), ("Sinyalizasyon", 5)])
            oncelik = U.agirlikli(rng, [("Düşük", 26), ("Orta", 44), ("Yüksek", 24), ("Acil", 6)])
            hedef = {"Düşük": 120, "Orta": 60, "Yüksek": 24, "Acil": 6}[oncelik]
            sure = max(0.5, rng.gauss(hedef * 0.8, hedef * 0.45))
            cozuldu = rng.random() < 0.9
            cozum = gun + dt.timedelta(days=sure / 24.0) if cozuldu else None
            sorumlu = mud["Fen İşleri Müdürlüğü"] if tur not in ("Devrilen ağaç",) \
                else mud["Park ve Bahçeler Müdürlüğü"]
            d.w(T.infrastructure_fault).yaz(
                infrastructure_fault_id=fid, report_date=gun, neighborhood_id=m,
                street_id=rng.choice(w.sokak_by_mah[m]), fault_type=tur, severity=oncelik,
                source=U.agirlikli(rng, [("Vatandaş", 52), ("Zabıta", 17),
                                         ("Rutin kontrol", 18), ("Muhtar", 8),
                                         ("Diğer kurum", 5)]),
                assigned_directorate_id=sorumlu,
                resolution_date=cozum if cozum and cozum <= U.BITIS else None,
                resolution_hours=round(sure, 2) if cozuldu else None,
                cost_amount=U.para(1800 * w.endeks(gun) * rng.uniform(0.2, 6.0)),
                status=("Çözüldü" if cozuldu else U.agirlikli(
                    rng, [("Devam ediyor", 58), ("Başka kuruma yönlendirildi", 32),
                          ("İptal", 10)])))

    # ================================================================ FILO
    vid = 0
    w.araclar = []
    for sinif, adet, yakit, mudler in ARAC_SINIF:
        for _ in range(adet):
            vid += 1
            model = rng.randrange(2006, 2027)
            edinim = dt.date(model, rng.randrange(1, 13), rng.randrange(1, 28))
            mulk = U.agirlikli(rng, [("Belediye malı", 58), ("Kiralık", 32),
                                     ("Şirket aracı", 10)])
            km = int((2026 - model + 1) * rng.uniform(9000, 42000))
            d.w(T.vehicle).yaz(
                vehicle_id=vid, plate_no=f"34 {rng.choice('ABCDEFGHJKLMNPRSTUVYZ')}"
                                         f"{rng.choice('ABCDEFGHJKLMNPRSTUVYZ')} {rng.randrange(100, 9999)}",
                vehicle_class=sinif, brand=rng.choice(MARKALAR), model_year=model,
                fuel_type=(yakit if rng.random() < 0.92 else
                           U.agirlikli(rng, [("Elektrik", 40), ("Hibrit", 35), ("LPG", 25)])),
                directorate_id=mud[rng.choice(mudler)], ownership=mulk,
                acquisition_date=edinim, odometer_km=km,
                status=U.agirlikli(rng, [("Aktif", 86), ("Bakımda", 7),
                                         ("Arızalı", 5), ("Hurdaya ayrıldı", 2)]),
                monthly_rental_cost=U.para(46000 * w.endeks(2026) / 9.92 * rng.uniform(0.6, 2.4)
                                           if mulk == "Kiralık" else 0))
            w.araclar.append({"id": vid, "sinif": sinif, "km": km, "edinim": edinim})

    soforler = [p["id"] for p in w.personeller if p["unvan"]["ad"] in ("Şoför", "İş Makinesi Operatörü")]
    flid, mid_ = 0, 0
    for a in w.araclar:
        bas = max(U.BASLANGIC, a["edinim"])
        if bas >= U.BITIS:
            continue
        haftalik = {"Çöp kamyonu": 3.2, "Süpürge aracı": 2.6, "Kamyon": 1.4, "Kamyonet": 1.1,
                    "Binek": 0.8, "Minibüs": 0.9, "İş makinesi": 1.2, "Vinç": 0.5,
                    "Arazöz": 1.6, "Cenaze aracı": 0.9, "Ambulans": 1.0}[a["sinif"]]
        adet = int((U.BITIS - bas).days / 7.0 * haftalik * rng.uniform(0.7, 1.2))
        km = max(0, a["km"] - int((U.BITIS - bas).days / 365.0 * 22000))
        for _ in range(adet):
            flid += 1
            gun = U.rastgele_gun(rng, bas, U.BITIS)
            litre = round({"Çöp kamyonu": rng.uniform(90, 220), "Süpürge aracı": rng.uniform(60, 140),
                           "Kamyon": rng.uniform(70, 180), "Kamyonet": rng.uniform(30, 70),
                           "Binek": rng.uniform(25, 55), "Minibüs": rng.uniform(40, 90),
                           "İş makinesi": rng.uniform(60, 160), "Vinç": rng.uniform(50, 130),
                           "Arazöz": rng.uniform(60, 150), "Cenaze aracı": rng.uniform(35, 75),
                           "Ambulans": rng.uniform(35, 80)}[a["sinif"]], 2)
            fiyat = round(6.85 / w.endeks(2026) * w.endeks(gun) * rng.uniform(0.95, 1.06), 3)
            km += rng.randrange(120, 900)
            d.w(T.fuel_log).yaz(
                fuel_log_id=flid, vehicle_id=a["id"], fill_date=gun, liters=litre,
                unit_price=fiyat, amount=U.para(litre * fiyat), odometer_km=km,
                station_name=rng.choice(["Belediye Akaryakıt İstasyonu", "Petrol Ofisi Şirinevler",
                                         "Opet Yenibosna", "Shell Kocasinan", "BP Bahçelievler"]),
                driver_employee_id=rng.choice(soforler) if soforler else None)
        for _ in range(int((U.BITIS - bas).days / 365.0 * rng.uniform(1.4, 4.2))):
            mid_ += 1
            gun = U.rastgele_gun(rng, bas, U.BITIS)
            tur = U.agirlikli(rng, [("Periyodik bakım", 40), ("Arıza onarımı", 26),
                                    ("Lastik", 12), ("Muayene", 10),
                                    ("Kasko/sigorta", 8), ("Kaza onarımı", 4)])
            parca = 4800 * w.endeks(gun) * rng.uniform(0.1, 6.0)
            iscilik = parca * rng.uniform(0.15, 0.6)
            d.w(T.vehicle_maintenance).yaz(
                vehicle_maintenance_id=mid_, vehicle_id=a["id"], service_date=gun,
                maintenance_type=tur, odometer_km=a["km"],
                parts_cost=U.para(parca), labor_cost=U.para(iscilik),
                total_cost=U.para(parca + iscilik),
                downtime_days=U.agirlikli(rng, [(1, 44), (2, 24), (3, 14), (5, 10), (12, 8)]),
                supplier_id=rng.choice(w.ted_by_kat.get("Araç kiralama",
                                                        [t["id"] for t in w.tedarikciler])))

    # ------------------------------------------------------ tesis enerji tuketimi
    feid = 0
    for t in w.tesisler:
        for ay in U.aylar():
            feid += 1
            kis = ay.month in (11, 12, 1, 2, 3)
            elk = t["alan"] * rng.uniform(1.6, 4.2) * (1.25 if ay.month in (6, 7, 8) else 1.0)
            gaz = t["alan"] * (rng.uniform(1.1, 2.8) if kis else rng.uniform(0.05, 0.4))
            su = t["alan"] * rng.uniform(0.05, 0.35)
            fe = w.endeks(ay)
            d.w(T.facility_energy_usage).yaz(
                facility_energy_usage_id=feid, municipal_facility_id=t["id"], period_month=ay,
                electricity_kwh=round(elk, 2), electricity_cost=U.para(elk * 1.42 / 9.92 * fe),
                gas_m3=round(gaz, 2), gas_cost=U.para(gaz * 3.9 / 9.92 * fe),
                water_m3=round(su, 2), water_cost=U.para(su * 28 / 9.92 * fe),
                solar_generation_kwh=round(elk * rng.uniform(0.05, 0.3), 2)
                if t["yil"] >= 2018 and rng.random() < 0.35 else 0)

    # ========================================================= TEMIZLIK / CEVRE
    wid = 0
    cop_araclari = [a["id"] for a in w.araclar if a["sinif"] == "Çöp kamyonu"]
    for gun in U.gunler():
        for m in w.mahalleler:
            wid += 1
            nfs = w.nufus(m["id"], gun.year)
            kisi_basi = 1.02 * U.mevsim_carpani(gun, 0.11, 0.62)   # kg/kisi/gun
            if gun.month in (6, 7, 8):
                kisi_basi *= 1.06
            evsel = nfs * kisi_basi / 1000.0 * rng.uniform(0.92, 1.08)
            iri = evsel * rng.uniform(0.02, 0.07)
            pazar = evsel * (rng.uniform(0.04, 0.11) if gun.weekday() in (1, 4, 5) else 0.0)
            toplam = evsel + iri + pazar
            d.w(T.waste_collection).yaz(
                waste_collection_id=wid, collection_date=gun, neighborhood_id=m["id"],
                route_code=f"G-{m['id']:02d}-{rng.randrange(1, 4)}",
                household_waste_ton=round(evsel, 3), bulky_waste_ton=round(iri, 3),
                market_waste_ton=round(pazar, 3), total_ton=round(toplam, 3),
                trip_count=max(1, int(toplam / 7.5) + 1),
                vehicle_id=rng.choice(cop_araclari) if cop_araclari else None,
                crew_size=U.agirlikli(rng, [(3, 40), (4, 38), (5, 22)]),
                transfer_station=rng.choice(["Halkalı Aktarma İstasyonu",
                                             "Yenibosna Aktarma İstasyonu"]),
                disposal_cost=U.para(toplam * 620 / w.endeks(2026) * w.endeks(gun)))

    # geri donusum
    gid = 0
    for ay in U.aylar():
        for m in w.mahalleler:
            gid += 1
            nfs = w.nufus(m["id"], ay.year)
            # sifir atik ile yillar icinde artan oran
            oran = 0.062 + 0.011 * (ay.year - 2019) + rng.uniform(-0.008, 0.012)
            toplam_atik = nfs * 1.02 * 30 / 1000.0
            geri = toplam_atik * oran
            d.w(T.recycling_stat).yaz(
                recycling_stat_id=gid, period_month=ay, neighborhood_id=m["id"],
                paper_ton=round(geri * 0.41, 3), plastic_ton=round(geri * 0.27, 3),
                glass_ton=round(geri * 0.16, 3), metal_ton=round(geri * 0.09, 3),
                organic_ton=round(geri * 0.07, 3),
                waste_oil_liter=round(nfs * rng.uniform(0.002, 0.007), 2),
                battery_kg=round(nfs * rng.uniform(0.0008, 0.0025), 2),
                electronic_waste_kg=round(nfs * rng.uniform(0.004, 0.014), 2),
                recycling_rate=round(oran * 100, 2),
                revenue_amount=U.para(geri * 2600 / w.endeks(2026) * w.endeks(ay)),
                container_count=int(nfs / rng.uniform(180, 320)))

    # hava kalitesi
    aqid = 0
    for gun in U.gunler():
        kis = gun.month in (11, 12, 1, 2, 3)
        for ist, mah in ISTASYONLAR:
            aqid += 1
            pm10 = max(6, rng.gauss(58 if kis else 38, 18))
            pm25 = pm10 * rng.uniform(0.45, 0.68)
            aqi = int(min(320, pm25 * 2.6 + rng.uniform(-10, 18)))
            kat = ("İyi" if aqi <= 50 else "Orta" if aqi <= 100 else
                   "Hassas" if aqi <= 150 else "Sağlıksız" if aqi <= 200 else
                   "Kötü" if aqi <= 300 else "Tehlikeli")
            d.w(T.air_quality_measurement).yaz(
                air_quality_measurement_id=aqid, measurement_date=gun, station_name=ist,
                neighborhood_id=mah, pm10=round(pm10, 2), pm25=round(pm25, 2),
                so2=round(max(1, rng.gauss(9 if kis else 5, 4)), 2),
                no2=round(max(3, rng.gauss(46 if kis else 32, 15)), 2),
                o3=round(max(4, rng.gauss(38 if not kis else 22, 14)), 2),
                co=round(max(0.1, rng.gauss(0.9 if kis else 0.5, 0.35)), 2),
                aqi=aqi, aqi_category=kat,
                temperature_c=round(rng.gauss(
                    14.5 - 10.5 * U.mevsim_carpani(gun, 1.0, -0.25) + 10.5, 3.4), 2),
                noise_db=round(rng.gauss(64 if gun.weekday() < 5 else 59, 6), 2))
