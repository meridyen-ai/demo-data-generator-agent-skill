# -*- coding: utf-8 -*-
"""Sosyal yardim, saglik, veteriner, kultur-spor-kutuphane hizmetleri."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

YARDIM_TURU = [
    ("Gıda yardımı", 24, "Koli", 1250),
    ("Nakdi yardım", 19, None, 3200),
    ("Yakacak yardımı", 12, "Ton", 2800),
    ("Eğitim yardımı", 11, None, 1900),
    ("Kira yardımı", 6, None, 6500),
    ("Sağlık/ilaç yardımı", 7, None, 1600),
    ("Engelli desteği", 5, None, 2400),
    ("Giyim yardımı", 6, "Adet", 900),
    ("Beyaz eşya", 2, "Adet", 12000),
    ("Asker ailesi yardımı", 3, None, 2100),
    ("Cenaze yardımı", 2, None, 4200),
    ("Yeni doğan desteği", 3, "Adet", 1500),
]

ETKINLIK_ADLARI = {
    "Konser": ["Türk Sanat Müziği Konseri", "Halk Konseri", "Gençlik Konseri",
               "Ramazan Akşamı Konseri", "Cumhuriyet Konseri", "Tasavvuf Musikisi Gecesi"],
    "Tiyatro": ["Çocuk Tiyatrosu: Uçurtmanın Peşinde", "Komedi Oyunu: Komşu Kapısı",
                "Klasik Oyun: Bir Yaz Gecesi Rüyası", "Gölge Oyunu Karagöz-Hacivat"],
    "Sinema": ["Açık Hava Sineması", "Çocuk Sineması Günleri", "Belgesel Gösterimi"],
    "Söyleşi/konferans": ["Kariyer Söyleşisi", "Sağlıklı Yaşam Semineri",
                          "Aile İçi İletişim Konferansı", "Deprem Bilinci Semineri",
                          "Girişimcilik Buluşması", "Bağımlılıkla Mücadele Semineri"],
    "Festival": ["Çocuk Şenliği", "Kitap Fuarı", "Yaz Festivali", "Bahar Şenliği",
                 "Gastronomi Günleri", "Bahçelievler Kültür Sanat Festivali"],
    "Çocuk etkinliği": ["Yarıyıl Çocuk Şenliği", "23 Nisan Çocuk Bayramı Etkinliği",
                        "Masal Saati", "Bilim Atölyesi"],
    "Sergi": ["El Sanatları Sergisi", "Resim Sergisi", "Fotoğraf Sergisi",
              "Hat ve Ebru Sergisi"],
    "Ramazan etkinliği": ["Ramazan Sokağı Etkinlikleri", "İftar Programı",
                          "Teravih Sonrası Konser", "Hacivat Karagöz Gösterisi"],
    "Spor turnuvası": ["Mahalleler Arası Futbol Turnuvası", "Satranç Turnuvası",
                       "Yaz Spor Okulları Şenliği", "Voleybol Turnuvası"],
    "Anma töreni": ["15 Temmuz Anma Programı", "Çanakkale Zaferi Anma Programı",
                    "10 Kasım Atatürk'ü Anma Töreni", "18 Mart Şehitleri Anma"],
    "Kermes": ["Hayır Kermesi", "Okul Yararına Kermes", "El Emeği Kermesi"],
}

KITAP_TURU = [("Roman", 26), ("Çocuk", 21), ("Ders kaynak", 14), ("Tarih", 10),
              ("Kişisel gelişim", 9), ("Bilim", 7), ("Din", 6), ("Şiir", 4), ("Sanat", 3)]

KITAP_ADLARI = ["Kürk Mantolu Madonna", "Tutunamayanlar", "İnce Memed", "Çalıkuşu",
                "Sinekli Bakkal", "Serenad", "Beyaz Kale", "Kuyucaklı Yusuf",
                "Şeker Portakalı", "Küçük Prens", "Simyacı", "Sefiller", "Suç ve Ceza",
                "Yaban", "Aylak Adam", "Puslu Kıtalar Atlası", "Nutuk", "Safahat",
                "Mai ve Siyah", "Araba Sevdası", "Bir Bilim Adamının Romanı",
                "Fareler ve İnsanlar", "Hayvan Çiftliği", "1984", "Dokuzuncu Hariciye Koğuşu",
                "Anayurt Oteli", "Sessiz Ev", "Benim Adım Kırmızı", "Devlet Ana",
                "Yer Demir Gök Bakır", "Bilinmeyen Bir Kadının Mektubu", "Momo",
                "Pinokyo", "Heidi", "Polyanna", "Define Adası", "Uçurtma Avcısı"]

BRANSLAR = [("Yüzme", 22), ("Fitness", 19), ("Basketbol", 11), ("Futbol", 14),
            ("Voleybol", 8), ("Tekvando", 7), ("Judo", 4), ("Masa tenisi", 4),
            ("Pilates", 6), ("Satranç", 3), ("Jimnastik", 2)]


def uret(w):
    d = w.depo
    rng = w.r("social")

    # ==================================================== SOSYAL YARDIM
    aid, pid = 0, 0
    dusuk_gelir_haneler = [h for h in w.haneler if h[3] <= 1]
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        # 2020-2021 pandemi doneminde basvuru patlamasi
        carpan = {2019: 1.0, 2020: 1.62, 2021: 1.48, 2022: 1.24,
                  2023: 1.36, 2024: 1.29, 2025: 1.22, 2026: 1.18}[yil]
        adet = int(9800 * gun_orani * carpan * rng.uniform(0.93, 1.08))
        for _ in range(adet):
            aid += 1
            hid, mid, uye, gi = dusuk_gelir_haneler[rng.randrange(len(dusuk_gelir_haneler))]
            cid = rng.choice(w.vat_by_mah[mid])
            tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            tur, _, birim, taban = _yardim(rng)
            gelir = (7500 + gi * 6500) * rng.uniform(0.6, 1.5) / w.endeks(2026) * w.endeks(tarih)
            puan = U.normal_int(rng, 62 - gi * 9 + uye * 3, 15, 0, 100)
            r = rng.random()
            durum = ("Onaylandı" if puan >= 55 and r < 0.93 else
                     "Reddedildi" if r < 0.82 else
                     "Eksik evrak" if r < 0.92 else
                     "İncelemede" if r < 0.97 else "İptal edildi")
            sure = U.normal_int(rng, 17, 12, 1, 120)
            karar = tarih + dt.timedelta(days=sure) if durum != "İncelemede" else None
            aylik = taban / w.endeks(2026) * w.endeks(tarih) * rng.uniform(0.7, 1.6) \
                if durum == "Onaylandı" else 0.0
            ay_sayisi = U.agirlikli(rng, [(1, 32), (3, 24), (6, 26), (12, 18)])
            d.w(T.social_aid_application).yaz(
                social_aid_application_id=aid, application_no=f"SY-{yil}-{aid:06d}",
                application_date=tarih, citizen_id=cid, household_id=hid,
                neighborhood_id=mid, aid_type=tur, household_income=U.para(gelir),
                household_size=uye,
                social_inquiry_date=tarih + dt.timedelta(days=rng.randrange(2, 20)),
                social_inquiry_score=puan, status=durum,
                rejection_reason=None if durum != "Reddedildi" else U.agirlikli(
                    rng, [("Gelir kriteri aşıldı", 38), ("SGK kaydı tespit edildi", 22),
                          ("Mükerrer başvuru", 14), ("İkamet uygun değil", 14),
                          ("Sosyal inceleme olumsuz", 12)]),
                decision_date=karar, processing_days=sure,
                approved_monthly_amount=U.para(aylik),
                support_duration_months=ay_sayisi if durum == "Onaylandı" else None)
            if durum == "Onaylandı" and karar:
                for k in range(ay_sayisi):
                    odeme = karar + dt.timedelta(days=30 * k)
                    if odeme > U.BITIS:
                        break
                    pid += 1
                    d.w(T.aid_payment).yaz(
                        aid_payment_id=pid, social_aid_application_id=aid, citizen_id=cid,
                        neighborhood_id=mid, payment_date=odeme, aid_type=tur,
                        payment_form=U.agirlikli(rng, [("Banka havalesi", 34),
                                                       ("Kent Kart yükleme", 28),
                                                       ("Ayni teslim", 30), ("Vezne", 8)]),
                        amount=U.para(aylik * rng.uniform(0.95, 1.05)),
                        quantity=rng.randrange(1, 4) if birim else None, unit=birim,
                        delivered_by=rng.choice(["Sosyal Yardım Ekibi 1", "Sosyal Yardım Ekibi 2",
                                                 "Sosyal Yardım Ekibi 3", "Muhtarlık",
                                                 "Kargo ile teslim"]))

    # ---------------------------------------------------------------- asevi
    sid = 0
    for gun in U.gunler():
        sid += 1
        ramazan = _ramazan_mi(gun)
        taban = 2100 + 130 * (gun.year - 2019)
        uretilen = int(taban * (1.85 if ramazan else 1.0) * U.mevsim_carpani(gun, 0.14, 0.55)
                       * rng.uniform(0.92, 1.09))
        eve = int(uretilen * rng.uniform(0.52, 0.68))
        maliyet = uretilen * 42 / w.endeks(2026) * w.endeks(gun)
        d.w(T.soup_kitchen_daily).yaz(
            soup_kitchen_daily_id=sid, service_date=gun, facility_name="Belediye Aşevi",
            meals_produced=uretilen, meals_delivered_home=eve,
            meals_served_onsite=uretilen - eve,
            beneficiary_household_count=int(eve / rng.uniform(2.1, 3.2)),
            food_cost=U.para(maliyet), cost_per_meal=U.para(maliyet / uretilen),
            is_ramadan=ramazan)

    # ==================================================== SAGLIK / VETERINER
    saglik_tesis = [t for t in w.tesisler if t["tur"] == "Sağlık merkezi"
                    and "Hayvan" not in t["ad"]]
    w.saglik_merkezleri = []
    for i, t in enumerate(saglik_tesis, 1):
        d.w(T.health_center).yaz(
            health_center_id=i, center_name=t["ad"], neighborhood_id=t["mah"],
            service_types="Diş polikliniği, fizik tedavi, psikolojik danışmanlık, "
                          "diyetisyen, evde sağlık, gebe izlem",
            doctor_count=U.normal_int(rng, 6, 3, 1, 14),
            nurse_count=U.normal_int(rng, 11, 5, 2, 26),
            opening_year=t["yil"], daily_capacity=int(t["kap"] * rng.uniform(0.5, 1.2)))
        w.saglik_merkezleri.append({"id": i, "mah": t["mah"]})

    vid = 0
    for gun in U.gunler():
        if gun.weekday() >= 5:
            continue
        for hc in w.saglik_merkezleri:
            adet = U.normal_int(rng, 62, 22, 5, 160)
            if gun.year in (2020, 2021):
                adet = int(adet * 0.72)
            for _ in range(adet):
                vid += 1
                cid = rng.choice(w.vat_by_mah[hc["mah"]]) if rng.random() < 0.72 \
                    else rng.choice(w.vat_by_mah[rng.choice(w.mahalleler)["id"]])
                _, mah, dogum, cins = w.vatandaslar[cid - 1]
                yas = gun.year - dogum.year
                hizmet = U.agirlikli(rng, [("Diş polikliniği", 24), ("Fizik tedavi", 17),
                                           ("Aile hekimliği destek", 14),
                                           ("Psikolojik danışmanlık", 11),
                                           ("Tansiyon-şeker ölçüm", 12), ("Diyetisyen", 7),
                                           ("Gebe izlem", 5), ("Evde sağlık", 6), ("Aşı", 4)])
                d.w(T.clinic_visit).yaz(
                    clinic_visit_id=vid, visit_date=gun, health_center_id=hc["id"],
                    citizen_id=cid, neighborhood_id=mah, service_type=hizmet,
                    age_at_visit=yas, gender=cins,
                    diagnosis_group=U.agirlikli(rng, [("Kas-iskelet", 20), ("Diş-ağız", 22),
                                                      ("Metabolik", 13), ("Psikolojik", 10),
                                                      ("Kardiyovasküler", 11), ("Solunum", 9),
                                                      ("Koruyucu sağlık", 8),
                                                      ("Gebelik izlem", 4), ("Diğer", 3)]),
                    is_first_visit=rng.random() < 0.38,
                    referral_made=rng.random() < 0.12,
                    service_cost=U.para(210 / w.endeks(2026) * w.endeks(gun) * rng.uniform(0.5, 3.2)))

    # veteriner
    vetid = 0
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        adet = int(3900 * gun_orani * (1 + 0.06 * (yil - 2019)) * rng.uniform(0.9, 1.12))
        for _ in range(adet):
            vetid += 1
            gun = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            islem = U.agirlikli(rng, [("Kısırlaştırma", 26), ("Aşılama", 27), ("Tedavi", 16),
                                      ("Mikroçip takma", 9), ("Sahiplendirme", 7),
                                      ("Barınağa alım", 8), ("Doğal ortama bırakma", 5),
                                      ("Kuduz şüphesi gözlem", 2)])
            tur = U.agirlikli(rng, [("Köpek", 58), ("Kedi", 38), ("Kuş", 3), ("Diğer", 1)])
            barinak = rng.randrange(1, 45) if islem in ("Barınağa alım", "Kısırlaştırma",
                                                        "Tedavi", "Kuduz şüphesi gözlem") else 0
            d.w(T.veterinary_record).yaz(
                veterinary_record_id=vetid, record_date=gun,
                neighborhood_id=U.agirlikli(rng, [(m["id"], m["nufus2026"]) for m in w.mahalleler]),
                animal_type=tur, procedure_type=islem,
                estimated_age_months=U.normal_int(rng, 30, 24, 1, 168),
                gender="E" if rng.random() < 0.51 else "D",
                microchip_no=f"TR{rng.randrange(10**11, 10**12)}" if rng.random() < 0.62 else None,
                shelter_days=barinak, adopted=islem == "Sahiplendirme",
                cost_amount=U.para({"Kısırlaştırma": 1400, "Aşılama": 260, "Tedavi": 950,
                                    "Mikroçip takma": 180, "Sahiplendirme": 120,
                                    "Barınağa alım": 620, "Doğal ortama bırakma": 90,
                                    "Kuduz şüphesi gözlem": 1100}[islem]
                                   / w.endeks(2026) * w.endeks(gun) * rng.uniform(0.7, 1.5)),
                veterinarian_name=U.kisi_adi(rng)[0])

    # ==================================================== KULTUR / SPOR
    eid, atid = 0, 0
    kultur_tesis = [t for t in w.tesisler
                    if t["tur"] in ("Kültür merkezi", "Spor tesisi", "Gençlik merkezi",
                                    "Sosyal tesis")]
    for yil in U.YILLAR:
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        gun_orani = ((yil_sonu - dt.date(yil, 1, 1)).days + 1) / 365.0
        adet = int(560 * gun_orani * rng.uniform(0.9, 1.15))
        if yil in (2020, 2021):
            adet = int(adet * 0.45)
        for _ in range(adet):
            eid += 1
            kat = U.agirlikli(rng, [(k, v) for k, v in
                                    [("Konser", 14), ("Tiyatro", 13), ("Sinema", 9),
                                     ("Söyleşi/konferans", 16), ("Festival", 5),
                                     ("Çocuk etkinliği", 13), ("Sergi", 8),
                                     ("Ramazan etkinliği", 7), ("Spor turnuvası", 8),
                                     ("Anma töreni", 5), ("Kermes", 2)]])
            tarih = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
            tesis = rng.choice(kultur_tesis)
            kap = int(tesis["kap"] * rng.uniform(0.5, 1.0))
            katilim = int(kap * rng.uniform(0.42, 1.05))
            ucretsiz = rng.random() < 0.86
            bilet = 0.0 if ucretsiz else round(45 / w.endeks(2026) * w.endeks(tarih)
                                               * rng.uniform(0.6, 3.0), 2)
            maliyet = katilim * 95 / w.endeks(2026) * w.endeks(tarih) * rng.uniform(0.4, 3.2)
            d.w(T.event).yaz(
                event_id=eid, event_name=rng.choice(ETKINLIK_ADLARI[kat]),
                event_category=kat, event_date=tarih, municipal_facility_id=tesis["id"],
                neighborhood_id=tesis["mah"], venue_name=tesis["ad"], capacity=kap,
                attendance=katilim, is_free=ucretsiz, ticket_price=U.para(bilet),
                cost_amount=U.para(maliyet), revenue_amount=U.para(bilet * katilim),
                satisfaction_score=round(min(5, max(2.4, rng.gauss(4.28, 0.42))), 2),
                target_audience=U.agirlikli(rng, [("Genel", 52), ("Çocuk", 18), ("Genç", 12),
                                                  ("Kadın", 10), ("Yaşlı", 5), ("Engelli", 3)]))
            kayitli = int(katilim * rng.uniform(0.25, 0.6))
            havuz = w.vat_by_mah[tesis["mah"]]
            for _ in range(kayitli):
                atid += 1
                d.w(T.event_attendance).yaz(
                    event_attendance_id=atid, event_id=eid, citizen_id=rng.choice(havuz),
                    registration_date=tarih - dt.timedelta(days=rng.randrange(0, 21)),
                    attended=rng.random() < 0.83,
                    channel=U.agirlikli(rng, [("Mobil uygulama", 38), ("Web", 26),
                                              ("Telefon", 14), ("Yerinde", 22)]),
                    companion_count=U.agirlikli(rng, [(0, 46), (1, 30), (2, 16), (3, 8)]),
                    rating=U.agirlikli(rng, [(5, 48), (4, 32), (3, 13), (2, 5), (1, 2)]))

    # kutuphane
    kutuphaneler = [t for t in w.tesisler if t["tur"] == "Kütüphane"]
    w.kutuphaneler = []
    for i, t in enumerate(kutuphaneler, 1):
        d.w(T.library).yaz(
            library_id=i, library_name=t["ad"], neighborhood_id=t["mah"],
            book_count=int(t["alan"] * rng.uniform(14, 32)),
            seat_count=int(t["kap"] * rng.uniform(0.4, 0.9)),
            member_count=int(t["alan"] * rng.uniform(3, 9)), opening_year=t["yil"],
            has_study_hall=rng.random() < 0.75, is_24_hours=rng.random() < 0.3)
        w.kutuphaneler.append({"id": i, "mah": t["mah"]})

    blid = 0
    for gun in U.gunler():
        if gun.weekday() == 6:
            continue
        for lib in w.kutuphaneler:
            adet = U.normal_int(rng, 16, 8, 0, 60)
            if gun.month in (6, 7, 8):
                adet = int(adet * 1.25)
            for _ in range(adet):
                blid += 1
                iade_plan = gun + dt.timedelta(days=15)
                gec = rng.random() < 0.21
                iade = (iade_plan + dt.timedelta(days=rng.randrange(1, 60)) if gec
                        else gun + dt.timedelta(days=rng.randrange(2, 16)))
                d.w(T.book_loan).yaz(
                    book_loan_id=blid, library_id=lib["id"],
                    citizen_id=rng.choice(w.vat_by_mah[lib["mah"]]),
                    book_title=rng.choice(KITAP_ADLARI),
                    book_category=U.agirlikli(rng, KITAP_TURU),
                    loan_date=gun, due_date=iade_plan,
                    return_date=iade if iade <= U.BITIS else None,
                    is_late=gec, late_days=(iade - iade_plan).days if gec else 0)

    # spor uyelikleri
    spor_tesis = [t for t in w.tesisler if t["tur"] == "Spor tesisi"]
    smid = 0
    for yil in U.YILLAR:
        for donem_ay in (1, 4, 7, 10):
            bas = dt.date(yil, donem_ay, 1)
            if bas > U.BITIS:
                continue
            adet = int(1500 * rng.uniform(0.85, 1.15))
            if yil in (2020, 2021):
                adet = int(adet * 0.5)
            for _ in range(adet):
                smid += 1
                t = rng.choice(spor_tesis)
                cid = rng.choice(w.vat_by_mah[t["mah"]])
                _, mah, dogum, cins = w.vatandaslar[cid - 1]
                yas = yil - dogum.year
                yg = ("Çocuk" if yas < 15 else "Genç" if yas < 25
                      else "65+" if yas >= 65 else "Yetişkin")
                indirimli = rng.random() < 0.46
                ucret = 0.0 if indirimli else round(950 / w.endeks(2026) * w.endeks(bas)
                                                    * rng.uniform(0.6, 2.4), 2)
                bitis = bas + dt.timedelta(days=rng.choice([90, 180, 365]))
                d.w(T.sports_membership).yaz(
                    sports_membership_id=smid, municipal_facility_id=t["id"], citizen_id=cid,
                    neighborhood_id=mah, branch=U.agirlikli(rng, BRANSLAR),
                    start_date=bas, end_date=bitis, age_group=yg, gender=cins,
                    fee_amount=U.para(ucret), is_discounted=indirimli,
                    visit_count=U.normal_int(rng, 34, 24, 0, 160),
                    status=("Aktif" if bitis > U.BITIS else
                            U.agirlikli(rng, [("Sona erdi", 84), ("İptal", 10),
                                              ("Dondurulmuş", 6)])))


def _yardim(rng):
    tur = U.agirlikli(rng, [((a, p, b, t), p) for a, p, b, t in YARDIM_TURU])
    return tur


def _ramazan_mi(gun):
    # yaklasik ramazan tarihleri
    araliklar = {2019: (5, 6, 6, 4), 2020: (4, 24, 5, 23), 2021: (4, 13, 5, 12),
                 2022: (4, 2, 5, 1), 2023: (3, 23, 4, 20), 2024: (3, 11, 4, 9),
                 2025: (3, 1, 3, 29), 2026: (2, 18, 3, 19)}
    a = araliklar.get(gun.year)
    if not a:
        return False
    bas = dt.date(gun.year, a[0], a[1])
    bit = dt.date(gun.year, a[2], a[3])
    return bas <= gun <= bit
