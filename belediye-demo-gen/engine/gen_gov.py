# -*- coding: utf-8 -*-
"""Meclis, encumen, secim, mezarlik, otopark ve acil durum kayitlari."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

MECLIS_KONU = [
    ("İmar planı", 22, "1/1000 ölçekli uygulama imar planı tadilatı"),
    ("Bütçe", 6, "Mali yıl bütçe ve gelir tarifesi görüşmesi"),
    ("Tarife", 9, "Ücret ve harç tarifelerinin belirlenmesi"),
    ("Kadro", 8, "Norm kadro ihdas ve iptal işlemleri"),
    ("İsim verme", 5, "Park, sokak ve tesislere isim verilmesi"),
    ("Protokol", 11, "Kurumlar arası işbirliği protokolü onayı"),
    ("Borçlanma", 3, "Kredi kullanımı için yetki verilmesi"),
    ("Taşınmaz", 12, "Taşınmaz satış, tahsis ve kiralama işlemleri"),
    ("Komisyon raporu", 18, "İhtisas komisyonu raporunun görüşülmesi"),
    ("Diğer", 6, "Çeşitli gündem maddeleri"),
]

ENCUMEN_KONU = [("İmar cezası", 22), ("Para cezası", 19), ("İhale onayı", 14),
                ("İşyeri kapatma", 12), ("Kamulaştırma", 8), ("Tahsis", 9),
                ("Yıkım kararı", 7), ("Harcama izni", 9)]

MEZARLIKLAR = ["Bahçelievler Mezarlığı", "Yenibosna Mezarlığı", "Kocasinan Mezarlığı"]

PARTILER = [("A Partisi", 0.34), ("B Partisi", 0.31), ("C Partisi", 0.12),
            ("D Partisi", 0.09), ("E Partisi", 0.07), ("Bağımsız ve diğer", 0.07)]


def uret(w):
    d = w.depo
    rng = w.r("gov")
    mud = w.mud_by_ad

    # ------------------------------------------------------------ meclis
    mid, did = 0, 0
    for yil in U.YILLAR:
        for ay in range(1, 13):
            if dt.date(yil, ay, 1) > U.BITIS:
                break
            mid += 1
            tarih = dt.date(yil, ay, min(28, rng.randrange(2, 12)))
            if tarih > U.BITIS:
                tarih = U.BITIS
            tur = ("Bütçe görüşmesi" if ay == 11 else
                   "Kesin hesap" if ay == 5 else
                   "Olağanüstü" if rng.random() < 0.06 else "Olağan")
            gundem = U.normal_int(rng, 14, 6, 3, 38)
            karar_sayisi = int(gundem * rng.uniform(0.75, 1.0))
            d.w(T.council_meeting).yaz(
                council_meeting_id=mid, meeting_date=tarih, term_year=yil,
                session_type=tur, session_no=ay, member_count=45,
                attendee_count=U.normal_int(rng, 39, 4, 26, 45),
                agenda_item_count=gundem, decision_count=karar_sayisi,
                duration_minutes=U.normal_int(rng, 118, 46, 35, 340))
            for _ in range(karar_sayisi):
                did += 1
                konu, agirlik, ozet = U.agirlikli(rng, [((k, a, o), a) for k, a, o in MECLIS_KONU])
                sonuc = U.agirlikli(rng, [("Oybirliği", 54), ("Oyçokluğu", 31),
                                          ("Komisyona havale", 11), ("Reddedildi", 4)])
                kabul = (45 if sonuc == "Oybirliği" else
                         U.normal_int(rng, 27, 5, 16, 40) if sonuc == "Oyçokluğu" else
                         U.normal_int(rng, 15, 5, 3, 21))
                ret = 0 if sonuc == "Oybirliği" else U.normal_int(rng, 12, 5, 0, 26)
                d.w(T.council_decision).yaz(
                    council_decision_id=did, council_meeting_id=mid,
                    decision_no=f"{yil}/{did % 400 + 1}", decision_date=tarih,
                    topic=konu, summary=ozet,
                    proposing_directorate_id=rng.choice(w.mudurlukler)["id"],
                    vote_result=sonuc, yes_votes=kabul, no_votes=ret,
                    abstain_votes=max(0, 45 - kabul - ret),
                    neighborhood_id=(rng.choice(w.mahalleler)["id"]
                                     if konu in ("İmar planı", "İsim verme", "Taşınmaz")
                                     else None),
                    financial_impact=U.para(
                        rng.uniform(0.05, 40) * 1_000_000 / w.endeks(2026) * w.endeks(tarih)
                        if konu in ("Bütçe", "Borçlanma", "Taşınmaz", "Tarife") else 0))

    # ----------------------------------------------------------- encumen
    cid = 0
    for gun in U.gunler():
        if gun.weekday() != 3:            # encumen hafta bir toplanir
            continue
        for _ in range(U.normal_int(rng, 14, 6, 2, 38)):
            cid += 1
            konu = U.agirlikli(rng, ENCUMEN_KONU)
            d.w(T.committee_decision).yaz(
                committee_decision_id=cid, decision_date=gun,
                decision_no=f"{gun.year}/{cid % 900 + 1}", topic=konu,
                related_directorate_id=rng.choice(w.mudurlukler)["id"],
                neighborhood_id=rng.choice(w.mahalleler)["id"],
                result=U.agirlikli(rng, [("Kabul", 82), ("Ret", 11), ("Ertelendi", 7)]),
                financial_impact=U.para(
                    rng.uniform(0.002, 3.5) * 1_000_000 / w.endeks(2026) * w.endeks(gun)))

    # ------------------------------------------------------------- secim
    eid = 0
    for yil, tur in ((2019, "Yerel seçim"), (2023, "Genel seçim"), (2024, "Yerel seçim")):
        for m in w.mahalleler:
            secmen = int(w.nufus(m["id"], yil) * 0.71)
            katilim = rng.uniform(80, 90)
            gecerli = int(secmen * katilim / 100 * rng.uniform(0.975, 0.995))
            seg = m["segment"]
            paylar = []
            for parti, taban in PARTILER:
                kayma = {"Alt-Orta": 0.06, "Orta": 0.0, "Üst-Orta": -0.05}[seg]
                p = taban + (kayma if parti == "A Partisi" else -kayma / 5)
                paylar.append((parti, max(0.01, p * rng.uniform(0.86, 1.14))))
            toplam = sum(p for _, p in paylar)
            for parti, p in paylar:
                eid += 1
                oy = int(gecerli * p / toplam)
                d.w(T.election_result).yaz(
                    election_result_id=eid, election_year=yil, election_type=tur,
                    neighborhood_id=m["id"], party_code=parti, vote_count=oy,
                    vote_share=round(p / toplam * 100, 2), registered_voters=secmen,
                    turnout_rate=round(katilim, 2),
                    invalid_votes=int(secmen * katilim / 100 - gecerli))

    # ----------------------------------------------------------- mezarlik
    bid = 0
    for dr_id, tarih, mah, yas, cins in w.olumler:
        if rng.random() > 0.86:            # bir kismi ilce disinda defnedilir
            continue
        bid += 1
        hizmet = U.agirlikli(rng, [("Tam cenaze hizmeti", 62), ("Sadece nakil", 18),
                                   ("Sadece defin", 12), ("Gassal hizmeti", 8)])
        ucretsiz = rng.random() < 0.88
        maliyet = 4200 / w.endeks(2026) * w.endeks(tarih) * rng.uniform(0.6, 2.4)
        d.w(T.burial_record).yaz(
            burial_record_id=bid,
            burial_date=min(U.BITIS, tarih + dt.timedelta(days=rng.randrange(0, 2))),
            cemetery_name=U.agirlikli(rng, [(MEZARLIKLAR[0], 46), (MEZARLIKLAR[1], 33),
                                            (MEZARLIKLAR[2], 21)]),
            neighborhood_id=mah, death_record_id=dr_id, age_at_death=yas, gender=cins,
            service_type=hizmet, transport_distance_km=round(rng.uniform(2, 340), 2),
            fee_amount=U.para(0 if ucretsiz else maliyet * rng.uniform(0.3, 0.9)),
            cost_amount=U.para(maliyet), is_free_service=ucretsiz)

    # ------------------------------------------------------------ otopark
    w.otoparklar = []
    pid = 0
    for m in w.mahalleler:
        for _ in range(U.normal_int(rng, 3, 1, 1, 6)):
            pid += 1
            tur = U.agirlikli(rng, [("Yol üstü", 46), ("Açık alan", 28),
                                    ("Kapalı otopark", 16), ("Katlı otopark", 10)])
            kap = {"Yol üstü": rng.randrange(20, 90), "Açık alan": rng.randrange(40, 220),
                   "Kapalı otopark": rng.randrange(60, 300),
                   "Katlı otopark": rng.randrange(150, 700)}[tur]
            d.w(T.parking_lot).yaz(
                parking_lot_id=pid,
                lot_name=f"{m['ad']} {tur} Otoparkı {pid}", neighborhood_id=m["id"],
                lot_type=tur, capacity=kap,
                hourly_rate=U.para(18 / w.endeks(2026) * w.endeks(2026) * rng.uniform(0.6, 2.2)),
                monthly_rate=U.para(1450 * rng.uniform(0.7, 1.8)),
                opening_year=rng.randrange(2008, 2026),
                is_ev_charging=rng.random() < 0.22)
            w.otoparklar.append({"id": pid, "kap": kap, "tur": tur})

    ptid = 0
    for gun in U.gunler():
        if gun.year < 2021:                # dijital otopark sistemi 2021'de devreye alindi
            continue
        for lot in w.otoparklar:
            devir = 3.1 if lot["tur"] == "Yol üstü" else 2.1
            adet = int(lot["kap"] * devir * (0.55 if gun.weekday() >= 5 else 1.0)
                       * rng.uniform(0.55, 1.05) * 0.06)
            for _ in range(adet):
                ptid += 1
                giris_saat = U.agirlikli(rng, [(8, 10), (9, 12), (10, 11), (11, 10),
                                               (12, 9), (13, 9), (14, 10), (15, 9),
                                               (16, 8), (17, 7), (18, 5)])
                giris = dt.datetime(gun.year, gun.month, gun.day, giris_saat,
                                    rng.randrange(0, 60))
                sure = U.normal_int(rng, 96, 78, 8, 720)
                cikis = giris + dt.timedelta(minutes=sure)
                abone = rng.random() < 0.18
                saatlik = 18 / w.endeks(2026) * w.endeks(gun)
                tutar = 0.0 if abone else round(max(1, sure / 60.0) * saatlik * rng.uniform(0.9, 1.1), 2)
                d.w(T.parking_transaction).yaz(
                    parking_transaction_id=ptid, parking_lot_id=lot["id"], entry_at=giris,
                    entry_date=gun, exit_at=cikis if cikis.date() <= U.BITIS else None,
                    duration_minutes=sure,
                    vehicle_class=U.agirlikli(rng, [("Otomobil", 84), ("Ticari", 9),
                                                    ("Minibüs", 4), ("Motosiklet", 3)]),
                    payment_method=("Abonelik" if abone else U.agirlikli(
                        rng, [("Kredi kartı", 34), ("Nakit", 26), ("Mobil uygulama", 24),
                              ("Kent Kart", 16)])),
                    amount=U.para(tutar), is_subscriber=abone)

    # -------------------------------------------------------- acil durum
    eid2 = 0
    for gun in U.gunler():
        kis = gun.month in (11, 12, 1, 2, 3)
        taban = 3.4 if kis else 2.1
        # yagisli/firtinali gunlerde patlama
        if rng.random() < 0.035:
            taban *= rng.uniform(4, 12)
        for _ in range(U.normal_int(rng, int(taban), 2, 0, 60)):
            eid2 += 1
            tur = U.agirlikli(rng, [("Su baskını", 16 if kis else 7),
                                    ("Yangın desteği", 11),
                                    ("Kar mücadelesi", 14 if gun.month in (1, 2, 12) else 0),
                                    ("Fırtına hasarı", 9 if kis else 3),
                                    ("Ağaç devrilmesi", 14),
                                    ("Deprem ihbarı", 3), ("Çöken yol", 6),
                                    ("Asansörde mahsur", 12), ("Sel", 5 if kis else 2)])
            siddet = U.agirlikli(rng, [("Düşük", 34), ("Orta", 41), ("Yüksek", 20),
                                       ("Kritik", 5)])
            saat = rng.randrange(0, 24)
            d.w(T.emergency_call).yaz(
                emergency_call_id=eid2,
                call_at=dt.datetime(gun.year, gun.month, gun.day, saat, rng.randrange(0, 60)),
                call_date=gun,
                neighborhood_id=U.agirlikli(rng, [(m["id"], m["nufus2026"]) for m in w.mahalleler]),
                event_type=tur, severity=siddet,
                response_minutes=U.normal_int(rng, {"Kritik": 14, "Yüksek": 22,
                                                    "Orta": 38, "Düşük": 62}[siddet], 16, 4, 240),
                crew_count=U.agirlikli(rng, [(1, 44), (2, 30), (3, 16), (5, 10)]),
                vehicle_count=U.agirlikli(rng, [(1, 56), (2, 28), (3, 12), (4, 4)]),
                affected_building_count=U.agirlikli(rng, [(1, 62), (2, 18), (4, 12), (10, 8)]),
                affected_person_count=U.normal_int(rng, 6, 12, 0, 220),
                damage_estimate=U.para(rng.uniform(0, 900_000) / w.endeks(2026) * w.endeks(gun)),
                response_cost=U.para(rng.uniform(1500, 90_000) / w.endeks(2026) * w.endeks(gun)),
                status=U.agirlikli(rng, [("Tamamlandı", 91), ("Devam ediyor", 3),
                                         ("Diğer kuruma devredildi", 6)]))
