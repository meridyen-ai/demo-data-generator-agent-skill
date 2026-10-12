# -*- coding: utf-8 -*-
"""Bina, bagimsiz bolum, emlak beyani, emlak vergisi, CTV, ilan-reklam vergisi."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U

ODA = [("1+0", 6), ("1+1", 17), ("2+1", 41), ("3+1", 28), ("4+1", 8)]

CTV_TARIFE = ["1. Grup", "2. Grup", "3. Grup", "4. Grup", "5. Grup", "6. Grup", "7. Grup"]

ILAN_TURU = [("Işıklı tabela", 34), ("Işıksız tabela", 38), ("Bez afiş", 9),
             ("Bilbord", 6), ("Araç üzeri reklam", 8), ("Dijital ekran", 5)]


def uret(w):
    d = w.depo
    rng = w.r("property")

    # -------------------------------------------------------------------- bina
    w.binalar = []
    bid = 0
    for m in w.mahalleler:
        seg = m["segment"]
        for _ in range(m["bina"]):
            bid += 1
            yil = int(U.agirlikli(rng, [(1968, 8), (1978, 14), (1988, 21), (1996, 20),
                                        (2004, 14), (2012, 12), (2019, 8), (2023, 3)])
                      + rng.randrange(0, 8))
            yil = min(yil, 2026)
            kat = U.agirlikli(rng, [(3, 9), (4, 18), (5, 26), (6, 20), (7, 12),
                                    (8, 8), (10, 5), (14, 2)])
            daire_kat = U.agirlikli(rng, [(2, 34), (3, 26), (4, 30), (6, 10)])
            bb = kat * daire_kat + (0 if rng.random() < 0.55 else rng.randrange(1, 4))
            tasiyici = "Yığma" if yil < 1980 and rng.random() < 0.30 else U.agirlikli(
                rng, [("Betonarme", 94), ("Çelik", 4), ("Prefabrik", 2)])
            # deprem riski: eski + yigma daha riskli
            risk_puani = (2000 - min(yil, 2000)) / 12.0 + (14 if tasiyici == "Yığma" else 0) \
                + rng.uniform(-8, 8)
            if yil >= 2000:
                risk_puani -= 14
            risk = ("Acil riskli" if risk_puani > 26 else
                    "Yüksek" if risk_puani > 15 else
                    "Orta" if risk_puani > 4 else "Düşük")
            donusum = "Kapsam dışı"
            if risk in ("Yüksek", "Acil riskli"):
                donusum = U.agirlikli(rng, [("Kapsam dışı", 46), ("Başvuru yapıldı", 22),
                                            ("Riskli ilan edildi", 18), ("Yıkıldı", 8),
                                            ("Yeniden yapıldı", 6)])
            alan = bb * rng.uniform(78, 135)
            kullanim = U.agirlikli(rng, [("Konut", 78), ("Karma", 13), ("Ticari", 6),
                                         ("Kamu", 1), ("Eğitim", 1), ("Sağlık", 0.5),
                                         ("İbadet", 0.5)])
            d.w(T.building).yaz(
                building_id=bid, neighborhood_id=m["id"],
                street_id=rng.choice(w.sokak_by_mah[m["id"]]),
                building_no=str(rng.randrange(1, 220)) + (rng.choice(["", "", "", "/A", "/B"])),
                construction_year=yil, floor_count=kat, unit_count=bb,
                structure_type=tasiyici, usage_type=kullanim,
                has_occupancy_permit=rng.random() < (0.93 if yil >= 2000 else 0.71),
                has_elevator=kat >= 5 and rng.random() < (0.92 if yil >= 2000 else 0.48),
                earthquake_risk_class=risk, urban_renewal_status=donusum,
                total_area_m2=round(alan, 2))
            w.binalar.append({"id": bid, "mah": m["id"], "yil": yil, "bb": bb,
                              "kullanim": kullanim, "risk": risk, "seg": seg,
                              "donusum": donusum})

    # -------------------------------------------------------- bagimsiz bolumler
    # her binadan orneklem: veri hacmini kontrol altinda tutmak icin
    w.bolumler = []
    pid = 0
    for b in w.binalar:
        ornek = min(b["bb"], U.agirlikli(rng, [(2, 26), (3, 30), (4, 24), (6, 14), (8, 6)]))
        for k in range(ornek):
            pid += 1
            ticari = b["kullanim"] in ("Ticari",) or (b["kullanim"] == "Karma" and k == 0)
            tur = "İşyeri" if ticari else U.agirlikli(
                rng, [("Mesken", 93), ("Depo", 3), ("Otopark", 2), ("İşyeri", 2)])
            brut = rng.uniform(95, 165) if tur == "Mesken" else rng.uniform(30, 220)
            seg_carpan = {"Alt-Orta": 0.78, "Orta": 1.0, "Üst-Orta": 1.34}[b["seg"]]
            yas_carpan = 1.0 + max(-0.32, (b["yil"] - 2000) * 0.011)
            # 2026 rayic: m2 basina ~ 42.000 TL taban
            deger = brut * 42000 * seg_carpan * yas_carpan * rng.uniform(0.82, 1.24)
            if tur == "İşyeri":
                deger *= 1.45
            sahip = rng.choice(w.vat_by_mah[b["mah"]]) if rng.random() < 0.86 else None
            d.w(T.property_unit).yaz(
                property_unit_id=pid, building_id=b["id"],
                unit_no=str(k + 1), floor_no=rng.randrange(0, 12),
                unit_type=tur, gross_area_m2=round(brut, 2),
                room_layout="Dükkan" if tur == "İşyeri" else U.agirlikli(rng, ODA),
                heating_type=U.agirlikli(rng, [("Doğalgaz kombi", 76), ("Merkezi sistem", 16),
                                               ("Elektrik", 6), ("Soba", 2)]),
                current_value_try=U.para(deger), owner_citizen_id=sahip,
                is_rented=rng.random() < 0.41)
            w.bolumler.append({"id": pid, "mah": b["mah"], "tur": tur, "deger": deger,
                               "sahip": sahip, "bina": b["id"]})

    # ------------------------------------------------------------- emlak beyani
    w.beyanlar = []
    did = 0
    for p in w.bolumler:
        if p["sahip"] is None or rng.random() < 0.06:
            continue
        did += 1
        ilk_yil = rng.randrange(1998, 2027)
        beyan_tarih = dt.date(ilk_yil, rng.randrange(1, 13), rng.randrange(1, 28))
        muafiyet = "Yok"
        if p["tur"] == "Mesken" and rng.random() < 0.14:
            muafiyet = U.agirlikli(rng, [("Tek konut emekli", 58), ("Engelli", 18),
                                         ("Şehit yakını", 6), ("İşsiz", 18)])
        vergi_sinifi = {"Mesken": "Bina - Mesken", "İşyeri": "Bina - İşyeri",
                        "Depo": "Bina - İşyeri", "Otopark": "Bina - İşyeri",
                        "Arsa": "Arsa"}[p["tur"]]
        d.w(T.property_declaration).yaz(
            property_declaration_id=did, property_unit_id=p["id"], citizen_id=p["sahip"],
            declaration_date=beyan_tarih,
            declaration_type=U.agirlikli(rng, [("Yeni edinim", 54), ("Devir", 24),
                                               ("Miras", 13), ("Değişiklik", 9)]),
            declared_value_try=U.para(p["deger"] / w.endeks(2026) * w.endeks(max(2019, ilk_yil))
                                      * rng.uniform(0.55, 0.9)),
            tax_class=vergi_sinifi, exemption_type=muafiyet, first_tax_year=ilk_yil,
            is_active=rng.random() < 0.96)
        w.beyanlar.append({"id": did, "unit": p["id"], "cid": p["sahip"], "mah": p["mah"],
                           "deger2026": p["deger"], "sinif": vergi_sinifi,
                           "muaf": muafiyet, "ilk_yil": ilk_yil})

    # ------------------------------------------------- emlak vergisi tahakkuk/tahsil
    aid = 0
    tid = 0
    w.emlak_tahsilat_gunluk = {}
    for b in w.beyanlar:
        oran = {"Bina - Mesken": 0.002, "Bina - İşyeri": 0.004,
                "Arsa": 0.006, "Arazi": 0.002}[b["sinif"]]
        for yil in U.YILLAR:
            if yil < b["ilk_yil"]:
                continue
            if b["muaf"] != "Yok" and b["sinif"] == "Bina - Mesken":
                continue
            matrah = b["deger2026"] / w.endeks(2026) * w.endeks(yil) * rng.uniform(0.42, 0.62)
            for taksit, ay in ((1, 5), (2, 11)):
                if yil == 2026 and ay == 11:
                    continue
                aid += 1
                vade = dt.date(yil, 5 if taksit == 1 else 11, 31 if ay == 5 else 30)
                tutar = matrah * oran / 2
                # tahsilat davranisi
                r = rng.random()
                if r < 0.71:
                    durum, odenen = "Ödendi", tutar
                elif r < 0.80:
                    durum, odenen = "Kısmi ödendi", tutar * rng.uniform(0.25, 0.85)
                elif r < 0.94:
                    durum, odenen = "Ödenmedi", 0.0
                elif r < 0.985:
                    durum, odenen = "Yapılandırıldı", tutar * rng.uniform(0.3, 1.0)
                else:
                    durum, odenen = "Terkin edildi", 0.0
                gecikme_zammi = 0.0
                odeme_gunu = None
                gec = False
                gecikme_gun = 0
                if odenen > 0:
                    if rng.random() < 0.72:
                        odeme_gunu = vade - dt.timedelta(days=rng.randrange(0, 60))
                    else:
                        gecikme_gun = rng.randrange(1, 420)
                        odeme_gunu = vade + dt.timedelta(days=gecikme_gun)
                        gec = True
                        gecikme_zammi = tutar * 0.025 * (gecikme_gun / 30.0)
                    if odeme_gunu > U.BITIS:
                        odeme_gunu = None
                        odenen = 0.0
                        durum = "Ödenmedi"
                        gecikme_zammi = tutar * 0.025 * 6
                d.w(T.property_tax_assessment).yaz(
                    property_tax_assessment_id=aid, property_declaration_id=b["id"],
                    citizen_id=b["cid"], neighborhood_id=b["mah"], tax_year=yil,
                    installment_no=taksit, due_date=vade,
                    assessed_value_try=U.para(matrah), tax_rate=round(oran * 1000, 4),
                    assessed_amount=U.para(tutar), penalty_amount=U.para(gecikme_zammi),
                    total_due=U.para(tutar + gecikme_zammi), status=durum)
                if odenen > 0 and odeme_gunu and U.BASLANGIC <= odeme_gunu <= U.BITIS:
                    tid += 1
                    d.w(T.property_tax_payment).yaz(
                        property_tax_payment_id=tid, property_tax_assessment_id=aid,
                        citizen_id=b["cid"], payment_date=odeme_gunu,
                        amount=U.para(odenen + gecikme_zammi),
                        channel=U.agirlikli(rng, [("İnternet", 28), ("Belediye veznesi", 26),
                                                  ("Mobil uygulama", 19), ("Banka", 14),
                                                  ("Kredi kartı", 9), ("PTT", 4)]),
                        is_late=gec, late_days=gecikme_gun)
                    w.emlak_tahsilat_gunluk[odeme_gunu] = \
                        w.emlak_tahsilat_gunluk.get(odeme_gunu, 0.0) + odenen + gecikme_zammi

    # ------------------------------------------------- cevre temizlik vergisi (CTV)
    cid = 0
    w.ctv_yillik = {y: 0.0 for y in U.YILLAR}
    for b in w.isyerleri:
        for yil in U.YILLAR:
            if b["acilis"].year > yil:
                continue
            if b["kapanis"] and b["kapanis"].year < yil:
                continue
            cid += 1
            grup = U.agirlikli(rng, [(g, wgt) for g, wgt in
                                     zip(CTV_TARIFE, [4, 7, 12, 20, 24, 21, 12])])
            taban = {"1. Grup": 9800, "2. Grup": 6200, "3. Grup": 4100, "4. Grup": 2600,
                     "5. Grup": 1500, "6. Grup": 900, "7. Grup": 520}[grup]
            tutar = taban / w.endeks(2026) * w.endeks(yil) * rng.uniform(0.85, 1.2)
            r = rng.random()
            durum = "Ödendi" if r < 0.74 else ("Kısmi ödendi" if r < 0.83 else "Ödenmedi")
            tahsil = tutar if durum == "Ödendi" else (tutar * rng.uniform(0.2, 0.8)
                                                     if durum == "Kısmi ödendi" else 0.0)
            w.ctv_yillik[yil] += tahsil
            d.w(T.environmental_tax).yaz(
                environmental_tax_id=cid, tax_year=yil, neighborhood_id=b["mah"],
                business_id=b["id"], property_unit_id=None, taxpayer_type="İşyeri",
                tariff_group=grup, assessed_amount=U.para(tutar),
                collected_amount=U.para(tahsil), status=durum)
    # mesken CTV'si su faturasi uzerinden tahsil edilir - mahalle bazli ozet kayit
    for yil in U.YILLAR:
        for m in w.mahalleler:
            cid += 1
            hane = int(w.nufus(m["id"], yil) / 3.1)
            tutar = hane * 46 / w.endeks(2026) * w.endeks(yil)
            tahsil = tutar * rng.uniform(0.88, 0.98)
            w.ctv_yillik[yil] += tahsil
            d.w(T.environmental_tax).yaz(
                environmental_tax_id=cid, tax_year=yil, neighborhood_id=m["id"],
                business_id=None, property_unit_id=None, taxpayer_type="Mesken",
                tariff_group="7. Grup", assessed_amount=U.para(tutar),
                collected_amount=U.para(tahsil), status="Ödendi")

    # --------------------------------------------------- ilan ve reklam vergisi
    rid = 0
    w.ilan_yillik = {y: 0.0 for y in U.YILLAR}
    for b in w.isyerleri:
        if rng.random() > 0.58:
            continue
        for yil in U.YILLAR:
            if b["acilis"].year > yil:
                continue
            if b["kapanis"] and b["kapanis"].year < yil:
                continue
            rid += 1
            tur = U.agirlikli(rng, ILAN_TURU)
            alan = round(abs(rng.gauss(4.2, 3.4)) + 0.5, 2)
            birim = {"Işıklı tabela": 720, "Işıksız tabela": 380, "Bez afiş": 95,
                     "Bilbord": 1450, "Araç üzeri reklam": 560,
                     "Dijital ekran": 2100}[tur] / w.endeks(2026) * w.endeks(yil)
            tutar = alan * birim
            tahsil = tutar * (1.0 if rng.random() < 0.79 else rng.uniform(0, 0.7))
            w.ilan_yillik[yil] += tahsil
            d.w(T.advertisement_tax).yaz(
                advertisement_tax_id=rid, tax_year=yil, business_id=b["id"],
                neighborhood_id=b["mah"], ad_type=tur, area_m2=alan,
                unit_rate=U.para(birim), assessed_amount=U.para(tutar),
                collected_amount=U.para(tahsil),
                permit_status=U.agirlikli(rng, [("İzinli", 84), ("İzinsiz", 12),
                                                ("Kaldırıldı", 4)]))
