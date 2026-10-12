# -*- coding: utf-8 -*-
"""Butce kalemleri, gelir/gider hareketleri, ihale, sozlesme, odeme emri, kredi."""
from __future__ import annotations

import datetime as dt

from . import tables as T
from . import util as U
from .world import ENFLASYON

# mudurluk bazli cari+yatirim harcama agirliklari (personel disi)
HARCAMA_AGIRLIK = {
    "Fen İşleri Müdürlüğü": 26.0,
    "Temizlik İşleri Müdürlüğü": 15.5,
    "Park ve Bahçeler Müdürlüğü": 9.0,
    "Sosyal Yardım İşleri Müdürlüğü": 7.5,
    "Kültür ve Sosyal İşler Müdürlüğü": 6.5,
    "Destek Hizmetleri Müdürlüğü": 6.0,
    "Kentsel Dönüşüm ve Afet İşleri Müdürlüğü": 4.5,
    "Mali Hizmetler Müdürlüğü": 4.0,
    "Sağlık İşleri Müdürlüğü": 3.0,
    "Gençlik ve Spor Hizmetleri Müdürlüğü": 3.0,
    "Bilgi İşlem Müdürlüğü": 2.6,
    "Zabıta Müdürlüğü": 2.2,
    "Veteriner İşleri Müdürlüğü": 1.9,
    "Ulaşım Hizmetleri Müdürlüğü": 1.8,
    "Basın Yayın ve Halkla İlişkiler Müdürlüğü": 1.7,
    "Emlak ve İstimlak Müdürlüğü": 1.5,
    "İmar ve Şehircilik Müdürlüğü": 1.2,
    "Kadın ve Aile Hizmetleri Müdürlüğü": 1.1,
    "Yapı Kontrol Müdürlüğü": 0.8,
    "Kentsel Tasarım Müdürlüğü": 0.7,
    "Plan ve Proje Müdürlüğü": 0.6,
    "Etüd Proje Müdürlüğü": 0.5,
    "İnsan Kaynakları ve Eğitim Müdürlüğü": 0.5,
    "Ruhsat ve Denetim Müdürlüğü": 0.4,
    "Hukuk İşleri Müdürlüğü": 0.4,
    "Yazı İşleri Müdürlüğü": 0.3,
    "Strateji Geliştirme Müdürlüğü": 0.3,
    "Muhtarlık İşleri Müdürlüğü": 0.3,
    "İşletme ve İştirakler Müdürlüğü": 0.3,
    "Teftiş Kurulu Müdürlüğü": 0.1,
}

# personel disi gider turu dagilimi -> (gider turu, ekonomik alt kod, pay)
GIDER_TURU = [
    ("Hizmet alımı", "03.5", 0.235),
    ("Yapım işi", "06.5", 0.175),
    ("Mal ve malzeme alımı", "03.2", 0.115),
    ("Bakım onarım", "03.8", 0.085),
    ("Enerji ve yakıt", "03.2", 0.075),
    ("Sosyal yardım", "05.4", 0.082),
    ("Makine teçhizat alımı", "06.1", 0.058),
    ("Kira gideri", "03.7", 0.036),
    ("Faiz gideri", "04.2", 0.028),
    ("Vergi ve harç", "05.8", 0.042),
    ("Diğer cari", "03.6", 0.045),
    ("Gayrimenkul büyük onarım", "06.7", 0.024),
]

GIDER_ACIKLAMA = {
    "Hizmet alımı": ["Personel çalıştırılmasına dayalı hizmet alımı", "Katı atık toplama hizmeti",
                     "Güvenlik hizmeti alımı", "Araç kiralama hizmeti", "Yemek hizmeti alımı",
                     "Temizlik hizmeti alımı", "Bilgi işlem destek hizmeti",
                     "Peyzaj bakım hizmeti", "Çağrı merkezi hizmeti"],
    "Yapım işi": ["Yol asfalt yapım işi", "Park yapım işi", "Kaldırım yenileme işi",
                  "Hizmet binası tadilat işi", "Spor tesisi yapım işi",
                  "Kapalı pazar yeri yapım işi", "Okul bahçesi düzenleme işi"],
    "Mal ve malzeme alımı": ["Kırtasiye malzemesi alımı", "Temizlik malzemesi alımı",
                             "İnşaat malzemesi alımı", "Gıda kolisi alımı",
                             "Tıbbi malzeme alımı", "Fidan ve çiçek alımı",
                             "Konteyner alımı", "Aydınlatma armatürü alımı"],
    "Bakım onarım": ["Bina bakım onarımı", "Asfalt yama çalışması", "Park bakım onarımı",
                     "Aydınlatma bakım onarımı", "Asansör bakımı"],
    "Enerji ve yakıt": ["Akaryakıt alımı", "Elektrik gideri", "Doğalgaz gideri", "Su gideri"],
    "Sosyal yardım": ["Nakdi yardım ödemesi", "Gıda yardımı", "Yakacak yardımı",
                      "Eğitim yardımı", "Kira yardımı", "Engelli destek ödemesi"],
    "Makine teçhizat alımı": ["Araç alımı", "İş makinesi alımı", "Bilgisayar ve donanım alımı",
                              "Mobilya alımı", "Jeneratör alımı"],
    "Kira gideri": ["Hizmet binası kirası", "Araç kirası", "Depo kirası", "Yazılım lisans kirası"],
    "Faiz gideri": ["İller Bankası kredi faizi", "Banka kredi faizi"],
    "Vergi ve harç": ["Gelirlerden ayrılan paylar", "Vergi ve harç ödemesi", "SGK prim borcu"],
    "Diğer cari": ["Temsil ve tanıtma gideri", "İlan ve reklam gideri", "Etkinlik gideri",
                   "Yolluk gideri", "Mahkeme ve icra gideri"],
    "Gayrimenkul büyük onarım": ["Hizmet binası büyük onarımı", "Kültür merkezi yenileme",
                                 "Pazar yeri büyük onarımı"],
}

GELIR_TURU = [
    # (gelir turu, ekonomik alt kod, hedef pay, islem adedi carpani)
    ("İller Bankası payı", "05.2", 0.470, 12),
    ("Emlak vergisi", "01.2", 0.0, 0),          # gercek tahsilattan gelir
    ("Çevre temizlik vergisi", "01.3", 0.0, 0),
    ("İlan ve reklam vergisi", "01.3", 0.0, 0),
    ("İşyeri ruhsat harcı", "01.9", 0.0, 0),
    ("İnşaat ruhsat harcı", "01.9", 0.052, 900),
    ("Kayıt ve suret harcı", "01.9", 0.008, 2600),
    ("Otopark geliri", "03.1", 0.021, 1400),
    ("Kira geliri", "03.6", 0.043, 320),
    ("İdari para cezası", "05.3", 0.026, 1800),
    ("Sosyal tesis geliri", "03.1", 0.019, 1200),
    ("Bağış ve yardım", "04.5", 0.011, 60),
    ("Arsa satışı", "06.1", 0.032, 14),
    ("Diğer gelirler", "05.9", 0.038, 2200),
]


_ALT_KOD_CACHE = {}


def _alt_kod(w, yon, alt):
    anahtar = (id(w), yon, alt)
    if anahtar not in _ALT_KOD_CACHE:
        _ALT_KOD_CACHE[anahtar] = next(
            (e["id"] for e in w.ekonomik if e["yon"] == yon and e["alt"] == alt), None)
    return _ALT_KOD_CACHE[anahtar]


def uret(w):
    d = w.depo
    rng = w.r("finance")
    mud_by_ad = w.mud_by_ad
    fonk_ids = [f["id"] for f in w.fonksiyonel]

    # mudurluk -> fonksiyonel kod esleme (kabaca)
    fonk_of_mud = {}
    for m in w.mudurlukler:
        ad = m["ad"]
        if ad.startswith("Temizlik") or ad.startswith("Veteriner"):
            kod = "05"
        elif ad.startswith("Fen") or ad.startswith("Ulaşım"):
            kod = "04"
        elif ad.startswith("İmar") or ad.startswith("Yapı") or ad.startswith("Plan") \
                or ad.startswith("Kentsel") or ad.startswith("Etüd") or ad.startswith("Emlak"):
            kod = "06"
        elif ad.startswith("Zabıta") or ad.startswith("Ruhsat"):
            kod = "03"
        elif ad.startswith("Sağlık"):
            kod = "07"
        elif ad.startswith("Kültür") or ad.startswith("Gençlik") or ad.startswith("Basın"):
            kod = "08"
        elif ad.startswith("Sosyal") or ad.startswith("Kadın"):
            kod = "10"
        elif ad.startswith("Park"):
            kod = "06"
        else:
            kod = "01"
        adaylar = [f["id"] for f in w.fonksiyonel if f["kod"] == kod]
        fonk_of_mud[m["id"]] = adaylar

    # ------------------------------------------------- mali yil olcek duzeltmesi
    # 5393 sayili Kanun m.49 personel gideri sinirina yakin kalmak icin:
    # personel maliyeti hedef giderin %32,5'ini asiyorsa butce hedefleri
    # (odenek, gider ve gelir birlikte) yukari olceklenir.
    for yil in U.YILLAR:
        my = w.mali_yil[yil]
        personel = w.yillik_personel_gideri[yil]
        olcek = max(1.0, personel / (0.325 * my["gider"]))
        for k in ("butce", "revize", "gider", "gelir"):
            my[k] *= olcek
        my["olcek"] = olcek
        d.w(T.fiscal_year).yaz(
            fiscal_year_id=my["id"], year=yil, budget_total_try=U.para(my["butce"]),
            revised_budget_try=U.para(my["revize"]),
            realized_revenue_try=U.para(my["gelir"]),
            realized_expense_try=U.para(my["gider"]),
            inflation_rate=ENFLASYON[yil],
            status="Kesin hesap onaylı" if yil <= 2025 else "Yıl içi",
            council_approval_date=my["onay"])

    # ---------------------------------------------------------------- ihaleler
    w.ihaleler, w.sozlesmeler = [], []
    tid, cid = 0, 0
    ihale_konulari = [
        ("Yol Bakım ve Asfalt Yapım İşi", "Yapım işi", "İnşaat ve taahhüt", "Fen İşleri Müdürlüğü"),
        ("Park ve Yeşil Alan Yapım İşi", "Yapım işi", "Peyzaj", "Park ve Bahçeler Müdürlüğü"),
        ("Kaldırım ve Bordür Yenileme İşi", "Yapım işi", "İnşaat ve taahhüt", "Fen İşleri Müdürlüğü"),
        ("Hizmet Binası Tadilat İşi", "Yapım işi", "İnşaat ve taahhüt", "Destek Hizmetleri Müdürlüğü"),
        ("Katı Atık Toplama ve Nakli Hizmet Alımı", "Hizmet alımı", "Temizlik hizmeti", "Temizlik İşleri Müdürlüğü"),
        ("Personel Çalıştırılmasına Dayalı Hizmet Alımı", "Hizmet alımı", "Temizlik hizmeti", "Destek Hizmetleri Müdürlüğü"),
        ("Özel Güvenlik Hizmet Alımı", "Hizmet alımı", "Güvenlik hizmeti", "Destek Hizmetleri Müdürlüğü"),
        ("Araç Kiralama Hizmet Alımı", "Hizmet alımı", "Araç kiralama", "Destek Hizmetleri Müdürlüğü"),
        ("Yemek Hazırlama ve Dağıtım Hizmet Alımı", "Hizmet alımı", "Gıda", "Sosyal Yardım İşleri Müdürlüğü"),
        ("Gıda Kolisi Alımı", "Mal alımı", "Gıda", "Sosyal Yardım İşleri Müdürlüğü"),
        ("Akaryakıt Alımı", "Mal alımı", "Akaryakıt", "Destek Hizmetleri Müdürlüğü"),
        ("Bilgi İşlem Donanım Alımı", "Mal alımı", "Bilişim", "Bilgi İşlem Müdürlüğü"),
        ("Kent Bilgi Sistemi Yazılım Alımı", "Hizmet alımı", "Bilişim", "Bilgi İşlem Müdürlüğü"),
        ("Kırtasiye ve Büro Malzemesi Alımı", "Mal alımı", "Kırtasiye", "Destek Hizmetleri Müdürlüğü"),
        ("Fidan ve Mevsimlik Çiçek Alımı", "Mal alımı", "Peyzaj", "Park ve Bahçeler Müdürlüğü"),
        ("LED Aydınlatma Armatürü Alımı", "Mal alımı", "Enerji", "Fen İşleri Müdürlüğü"),
        ("Tıbbi Malzeme ve İlaç Alımı", "Mal alımı", "Sağlık malzemesi", "Sağlık İşleri Müdürlüğü"),
        ("Kentsel Dönüşüm Etüt ve Proje Danışmanlığı", "Danışmanlık", "Danışmanlık", "Kentsel Dönüşüm ve Afet İşleri Müdürlüğü"),
        ("Spor Tesisi Yapım İşi", "Yapım işi", "İnşaat ve taahhüt", "Gençlik ve Spor Hizmetleri Müdürlüğü"),
        ("Kapalı Pazar Yeri Yapım İşi", "Yapım işi", "İnşaat ve taahhüt", "Fen İşleri Müdürlüğü"),
        ("Kültür Merkezi Ses ve Işık Sistemi Alımı", "Mal alımı", "Bilişim", "Kültür ve Sosyal İşler Müdürlüğü"),
        ("Hayvan Barınağı Bakım ve İlaçlama Hizmeti", "Hizmet alımı", "Sağlık malzemesi", "Veteriner İşleri Müdürlüğü"),
    ]
    for yil in U.YILLAR:
        adet = int(rng.uniform(150, 205) * (0.62 if yil == 2026 else 1.0))
        for _ in range(adet):
            tid += 1
            konu, is_turu, ted_kat, mud_ad = rng.choice(ihale_konulari)
            mud = mud_by_ad.get(mud_ad, 1)
            usul = U.agirlikli(rng, [("Açık ihale", 46), ("Doğrudan temin", 38),
                                     ("Pazarlık usulü", 12), ("Belli istekliler arasında", 4)])
            ilan = U.rastgele_gun(rng, dt.date(yil, 1, 1),
                                  min(U.BITIS, dt.date(yil, 12, 20)))
            ihale_gun = min(U.BITIS, ilan + dt.timedelta(days=rng.randrange(12, 45)))
            olcek = {"Açık ihale": rng.uniform(3.5, 45), "Doğrudan temin": rng.uniform(0.08, 0.9),
                     "Pazarlık usulü": rng.uniform(1.5, 12),
                     "Belli istekliler arasında": rng.uniform(8, 60)}[usul]
            yaklasik = olcek * 1_000_000 / w.endeks(2026) * w.endeks(ihale_gun)
            kirim = rng.uniform(2, 28)
            bedel = yaklasik * (1 - kirim / 100.0)
            durum = U.agirlikli(rng, [("Sonuçlandı", 88), ("İptal edildi", 6),
                                      ("İtiraz sürecinde", 3), ("Devam ediyor", 3)])
            adaylar = w.ted_by_kat.get(ted_kat, [t["id"] for t in w.tedarikciler])
            kazanan = rng.choice(adaylar) if durum == "Sonuçlandı" else None
            d.w(T.tender).yaz(
                tender_id=tid, tender_no=f"{yil}/{rng.randrange(100000, 999999)}",
                title=f"{yil} Yılı {konu}", directorate_id=mud, procurement_type=usul,
                work_type=is_turu, announcement_date=ilan, tender_date=ihale_gun,
                estimated_cost=U.para(yaklasik), winning_bid=U.para(bedel) if kazanan else None,
                bidder_count=U.normal_int(rng, 6, 4, 1, 24) if usul != "Doğrudan temin" else 1,
                winner_supplier_id=kazanan, discount_rate=round(kirim, 2), status=durum)
            w.ihaleler.append({"id": tid, "mud": mud, "kaz": kazanan, "bedel": bedel,
                               "gun": ihale_gun, "konu": konu, "durum": durum})
            if kazanan:
                cid += 1
                bas = ihale_gun + dt.timedelta(days=rng.randrange(10, 40))
                sure = rng.randrange(60, 720)
                bitis = bas + dt.timedelta(days=sure)
                artis = bedel * (rng.uniform(0, 0.20) if rng.random() < 0.34 else 0.0)
                if bitis <= U.BITIS:
                    gerc = round(rng.uniform(92, 100), 2)
                    sdurum = U.agirlikli(rng, [("Tamamlandı", 90), ("Feshedildi", 6),
                                               ("Tasfiye edildi", 4)])
                else:
                    gerc = round(rng.uniform(15, 88), 2)
                    sdurum = "Devam ediyor"
                odenen = (bedel + artis) * gerc / 100.0
                d.w(T.contract).yaz(
                    contract_id=cid, tender_id=tid, supplier_id=kazanan, directorate_id=mud,
                    contract_no=f"S-{yil}-{cid:05d}", subject=f"{yil} Yılı {konu}",
                    start_date=bas, end_date=bitis, contract_amount=U.para(bedel),
                    price_increase_amount=U.para(artis), paid_to_date=U.para(odenen),
                    completion_rate=gerc,
                    penalty_applied=U.para(bedel * rng.uniform(0.002, 0.03)
                                           if rng.random() < 0.16 else 0.0),
                    status=sdurum, guarantee_amount=U.para(bedel * 0.06))
                w.sozlesmeler.append({"id": cid, "ted": kazanan, "mud": mud, "bas": bas,
                                      "bit": bitis, "tutar": bedel + artis, "odenen": odenen})

    # ---------------------------------------------------------------- krediler
    krediler = [
        ("İller Bankası A.Ş.", "Altyapı yatırımları kredisi", dt.date(2018, 6, 12), 9, 62_000_000),
        ("İller Bankası A.Ş.", "Araç ve iş makinesi alımı kredisi", dt.date(2021, 3, 4), 7, 48_000_000),
        ("Ziraat Bankası", "Kültür merkezi yapım kredisi", dt.date(2022, 9, 19), 8, 95_000_000),
        ("Halkbank", "Kentsel dönüşüm finansmanı", dt.date(2023, 11, 7), 6, 180_000_000),
        ("Vakıfbank", "Nakit akış kredisi", dt.date(2024, 5, 22), 4, 240_000_000),
        ("İller Bankası A.Ş.", "Park ve rekreasyon yatırımı kredisi", dt.date(2025, 2, 14), 7, 310_000_000),
        ("Yatırım ve kalkınma", "Enerji verimliliği projesi", dt.date(2025, 10, 3), 6, 145_000_000),
    ]
    for i, (banka, amac, bas, yil_sayisi, anapara) in enumerate(krediler, 1):
        vade = dt.date(bas.year + yil_sayisi, bas.month, bas.day)
        gecen = max(0.0, (U.BITIS - bas).days / 365.0)
        kalan = max(0.0, anapara * (1 - gecen / yil_sayisi))
        d.w(T.municipal_loan).yaz(
            municipal_loan_id=i, lender=banka, purpose=amac, start_date=bas,
            maturity_date=vade, principal_amount=U.para(anapara),
            interest_rate=round(rng.uniform(11, 42), 2),
            outstanding_amount=U.para(kalan),
            annual_installment=U.para(anapara / yil_sayisi * 1.25),
            status="Kapandı" if kalan <= 0 else "Devam ediyor")

    # ------------------------------------------------------------ gider hareketi
    eid = 0
    w.gider_yillik_mud = {}
    toplam_agirlik = sum(HARCAMA_AGIRLIK.values())
    for yil in U.YILLAR:
        hedef_gider = w.mali_yil[yil]["gider"]
        personel = w.yillik_personel_gideri[yil]
        pers_disi = max(hedef_gider * 0.42, hedef_gider - personel)
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))

        # 1) personel giderleri: mudurluk x ay ozet kaydi
        for (y, mud), tutar in w.pers_gider.items():
            if y != yil:
                continue
            brut = tutar / 1.2275
            sgk = tutar - brut
            for ay in range(1, 13):
                if dt.date(yil, ay, 1) > U.BITIS:
                    break
                pay = 1 / 12.0
                for tur, alt, mikt in (("Personel gideri", "01.1", brut * pay),
                                       ("SGK devlet primi", "02.1", sgk * pay)):
                    eid += 1
                    gun = min(U.BITIS, dt.date(yil, ay, min(28, rng.randrange(24, 29))))
                    d.w(T.expense_transaction).yaz(
                        expense_transaction_id=eid, transaction_date=gun, year=yil,
                        directorate_id=mud,
                        functional_code_id=rng.choice(fonk_of_mud[mud]),
                        economic_code_id=_alt_kod(w, "Gider", alt),
                        expense_type=tur, supplier_id=None, contract_id=None,
                        neighborhood_id=None, amount=U.para(mikt), vat_amount=U.para(0),
                        total_amount=U.para(mikt),
                        document_no=f"MY-{yil}-{eid:07d}",
                        description=f"{yil}/{ay:02d} dönemi personel ödemesi")

        # 2) personel disi giderler
        for m in w.mudurlukler:
            pay = HARCAMA_AGIRLIK.get(m["ad"], 0.3) / toplam_agirlik
            mud_butce = pers_disi * pay * rng.uniform(0.90, 1.10)
            w.gider_yillik_mud[(yil, m["id"])] = mud_butce
            for tur, alt, tpay in GIDER_TURU:
                kalem = mud_butce * tpay * rng.uniform(0.75, 1.25)
                if kalem < 1000:
                    continue
                # islem adedi: buyuk kalemler daha cok parcaya bolunur
                adet = max(2, int(kalem / (85_000 * w.endeks(yil)) * rng.uniform(0.6, 1.5)))
                adet = min(adet, 420)
                agirliklar = [rng.uniform(0.3, 2.6) for _ in range(adet)]
                tw = sum(agirliklar)
                mud_soz = [s for s in w.sozlesmeler
                           if s["mud"] == m["id"] and s["bas"].year <= yil <= s["bit"].year]
                for a in agirliklar:
                    eid += 1
                    tutar = kalem * a / tw
                    gun = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
                    soz = rng.choice(mud_soz) if (mud_soz and rng.random() < 0.42) else None
                    ted = soz["ted"] if soz else (
                        rng.choice([t["id"] for t in w.tedarikciler])
                        if tur not in ("Sosyal yardım", "Faiz gideri", "Vergi ve harç") else None)
                    kdv = tutar * (0.20 if tur not in ("Sosyal yardım", "Faiz gideri",
                                                       "Vergi ve harç") else 0.0)
                    d.w(T.expense_transaction).yaz(
                        expense_transaction_id=eid, transaction_date=gun, year=yil,
                        directorate_id=m["id"],
                        functional_code_id=rng.choice(fonk_of_mud[m["id"]]),
                        economic_code_id=_alt_kod(w, "Gider", alt),
                        expense_type=tur, supplier_id=ted,
                        contract_id=soz["id"] if soz else None,
                        neighborhood_id=(rng.choice(w.mahalleler)["id"]
                                         if rng.random() < 0.55 else None),
                        amount=U.para(tutar), vat_amount=U.para(kdv),
                        total_amount=U.para(tutar + kdv),
                        document_no=f"GD-{yil}-{eid:07d}",
                        description=rng.choice(GIDER_ACIKLAMA[tur]))

    # ------------------------------------------------------------ gelir hareketi
    rid = 0
    # gercek tahsilat toplamlari
    emlak_yillik = {y: 0.0 for y in U.YILLAR}
    for gun, tutar in w.emlak_tahsilat_gunluk.items():
        emlak_yillik[gun.year] += tutar
    ruhsat_yillik = {y: 0.0 for y in U.YILLAR}
    for gun, tutar in w.ruhsat_geliri.items():
        if U.BASLANGIC <= gun <= U.BITIS:
            ruhsat_yillik[gun.year] += tutar

    for yil in U.YILLAR:
        hedef = w.mali_yil[yil]["gelir"]
        yil_sonu = min(U.BITIS, dt.date(yil, 12, 31))
        # gercek kaynaklardan gelenler
        sabitler = [
            ("Emlak vergisi", "01.2", emlak_yillik[yil], 900),
            ("Çevre temizlik vergisi", "01.3", w.ctv_yillik[yil], 700),
            ("İlan ve reklam vergisi", "01.3", w.ilan_yillik[yil], 350),
            ("İşyeri ruhsat harcı", "01.9", ruhsat_yillik[yil], 260),
        ]
        sabit_toplam = sum(x[2] for x in sabitler)
        kalan = max(hedef * 0.35, hedef - sabit_toplam)
        oransal = [(ad, alt, pay, adet) for ad, alt, pay, adet in GELIR_TURU if pay > 0]
        pay_toplam = sum(x[2] for x in oransal)

        kalemler = [(ad, alt, tutar, adet) for ad, alt, tutar, adet in sabitler]
        for ad, alt, pay, adet in oransal:
            kalemler.append((ad, alt, kalan * pay / pay_toplam, adet))

        for ad, alt, tutar, adet in kalemler:
            if tutar <= 0:
                continue
            adet = max(1, int(adet * (0.62 if yil == 2026 else 1.0)))
            agirliklar = [rng.uniform(0.3, 2.4) for _ in range(adet)]
            tw = sum(agirliklar)
            for a in agirliklar:
                rid += 1
                gun = U.rastgele_gun(rng, dt.date(yil, 1, 1), yil_sonu)
                if ad == "İller Bankası payı":
                    gun = min(yil_sonu, dt.date(yil, min(12, max(1, rid % 12 + 1)), 15))
                d.w(T.revenue_transaction).yaz(
                    revenue_transaction_id=rid, transaction_date=gun, year=yil,
                    economic_code_id=_alt_kod(w, "Gelir", alt), revenue_type=ad,
                    neighborhood_id=(rng.choice(w.mahalleler)["id"]
                                     if ad not in ("İller Bankası payı", "Bağış ve yardım")
                                     else None),
                    directorate_id=w.mud_by_ad["Mali Hizmetler Müdürlüğü"],
                    amount=U.para(tutar * a / tw),
                    channel=U.agirlikli(rng, [("Belediye veznesi", 24), ("İnternet", 26),
                                              ("Mobil uygulama", 17), ("Banka", 22),
                                              ("PTT", 4), ("Kredi kartı", 7)]),
                    document_no=f"TH-{yil}-{rid:07d}",
                    description=f"{ad} tahsilatı")

    # -------------------------------------------------------------- butce kalemi
    bid = 0
    for yil in U.YILLAR:
        # gider kalemleri
        for m in w.mudurlukler:
            gerceklesen_toplam = w.gider_yillik_mud.get((yil, m["id"]), 0.0)
            pers = sum(v for (y, dd), v in w.pers_gider.items()
                       if y == yil and dd == m["id"])
            kalemler = [("01.1", pers / 1.2275), ("02.1", pers - pers / 1.2275)]
            for tur, alt, tpay in GIDER_TURU:
                kalemler.append((alt, gerceklesen_toplam * tpay))
            birlesik = {}
            for alt, v in kalemler:
                birlesik[alt] = birlesik.get(alt, 0.0) + v
            for alt, gerc in birlesik.items():
                if gerc <= 0:
                    continue
                bid += 1
                baslangic = gerc / rng.uniform(0.72, 1.05)
                aktarma_in = baslangic * rng.uniform(0, 0.12)
                aktarma_out = baslangic * rng.uniform(0, 0.08)
                revize = baslangic + aktarma_in - aktarma_out
                d.w(T.budget_line).yaz(
                    budget_line_id=bid, year=yil, directorate_id=m["id"],
                    functional_code_id=rng.choice(fonk_of_mud[m["id"]]),
                    economic_code_id=_alt_kod(w, "Gider", alt), direction="Gider",
                    initial_appropriation=U.para(baslangic),
                    transfers_in=U.para(aktarma_in), transfers_out=U.para(aktarma_out),
                    revised_appropriation=U.para(revize), realized_amount=U.para(gerc),
                    realization_rate=round(gerc / revize * 100, 2) if revize else 0)
        # gelir kalemleri
        for ad, alt, pay, adet in GELIR_TURU:
            bid += 1
            tahmin = w.mali_yil[yil]["gelir"] * max(pay, 0.02) * rng.uniform(0.85, 1.15)
            gerc = tahmin * rng.uniform(0.78, 1.14)
            d.w(T.budget_line).yaz(
                budget_line_id=bid, year=yil,
                directorate_id=w.mud_by_ad["Mali Hizmetler Müdürlüğü"],
                functional_code_id=None,
                economic_code_id=_alt_kod(w, "Gelir", alt), direction="Gelir",
                initial_appropriation=U.para(tahmin), transfers_in=U.para(0),
                transfers_out=U.para(0), revised_appropriation=U.para(tahmin),
                realized_amount=U.para(gerc),
                realization_rate=round(gerc / tahmin * 100, 2))

    # ---------------------------------------------------------------- odeme emri
    oid = 0
    for s in w.sozlesmeler:
        adet = max(1, int((min(s["bit"], U.BITIS) - s["bas"]).days / 45))
        adet = min(adet, 18)
        if adet <= 0:
            continue
        for k in range(adet):
            gun = s["bas"] + dt.timedelta(days=int((k + 1) * 45))
            if gun > U.BITIS:
                break
            oid += 1
            brut = s["odenen"] / adet
            kesinti = brut * rng.uniform(0.04, 0.11)
            gecikme = U.normal_int(rng, 22, 18, 0, 160)
            odeme = gun + dt.timedelta(days=gecikme)
            odendi = odeme <= U.BITIS
            d.w(T.payment_order).yaz(
                payment_order_id=oid, order_no=f"OE-{gun.year}-{oid:06d}",
                order_date=gun, payment_date=odeme if odendi else None,
                supplier_id=s["ted"], contract_id=s["id"], directorate_id=s["mud"],
                gross_amount=U.para(brut), withholding_amount=U.para(kesinti),
                net_amount=U.para(brut - kesinti),
                status="Ödendi" if odendi else U.agirlikli(
                    rng, [("Beklemede", 82), ("İade edildi", 10), ("İptal", 8)]),
                delay_days=gecikme)
    # dogrudan temin / sozlesmesiz odemeler
    for _ in range(9000):
        oid += 1
        gun = U.rastgele_gun(rng)
        ted = rng.choice([t["id"] for t in w.tedarikciler])
        brut = 42_000 * w.endeks(gun) * rng.uniform(0.15, 6.0)
        kesinti = brut * rng.uniform(0.03, 0.10)
        gecikme = U.normal_int(rng, 18, 15, 0, 120)
        odeme = gun + dt.timedelta(days=gecikme)
        odendi = odeme <= U.BITIS
        d.w(T.payment_order).yaz(
            payment_order_id=oid, order_no=f"OE-{gun.year}-{oid:06d}",
            order_date=gun, payment_date=odeme if odendi else None,
            supplier_id=ted, contract_id=None,
            directorate_id=rng.choice(w.mudurlukler)["id"],
            gross_amount=U.para(brut), withholding_amount=U.para(kesinti),
            net_amount=U.para(brut - kesinti),
            status="Ödendi" if odendi else "Beklemede", delay_days=gecikme)
