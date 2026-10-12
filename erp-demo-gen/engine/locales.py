"""Locale-aware people/place pools (stdlib only).

The base names.py is US-centric. Industries that model a non-US company set
``"locale"`` in their tuning.json and get person names, cities, streets, phone
formats and country codes appropriate to the region instead.

Pools here are deliberately small-but-plausible: enough variety that a demo
never shows the same name twice on a screen, without pretending to be a real
census dataset.
"""
from __future__ import annotations

# ---------------------------------------------------------------- people ----

TR_FIRST_M = [
    "Mehmet", "Mustafa", "Ahmet", "Ali", "Hüseyin", "Hasan", "İbrahim", "Osman",
    "Yusuf", "Murat", "Ömer", "Ramazan", "Kemal", "Serkan", "Emre", "Burak",
    "Onur", "Volkan", "Tolga", "Kerem", "Baris", "Cem", "Deniz", "Ercan",
    "Fatih", "Gökhan", "Halil", "Ilker", "Kaan", "Levent", "Metin", "Necati",
    "Oguz", "Polat", "Recep", "Selim", "Tarik", "Ufuk", "Yavuz", "Zafer",
    "Alper", "Batuhan", "Caner", "Erdem", "Furkan", "Hakan", "Ismail", "Koray",
    "Mert", "Okan", "Sinan", "Taner", "Umut", "Yigit", "Bora", "Devrim",
]

TR_FIRST_F = [
    "Ayse", "Fatma", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Sultan",
    "Özlem", "Derya", "Sibel", "Gamze", "Merve", "Esra", "Büsra", "Seda",
    "Pinar", "Nurcan", "Aslihan", "Ebru", "Filiz", "Gülsah", "Hande", "Ipek",
    "Kübra", "Melike", "Nazli", "Selin", "Tugba", "Yasemin", "Aylin", "Burcu",
    "Ceren", "Dilek", "Ezgi", "Funda", "Gizem", "Hülya", "Irem", "Kader",
]

TR_LAST = [
    "Yilmaz", "Kaya", "Demir", "Sahin", "Çelik", "Yildiz", "Yildirim", "Öztürk",
    "Aydin", "Özdemir", "Arslan", "Dogan", "Kilic", "Aslan", "Çetin", "Kara",
    "Koç", "Kurt", "Özkan", "Simsek", "Polat", "Korkmaz", "Çakir", "Erdogan",
    "Güler", "Yavuz", "Kaplan", "Bulut", "Keskin", "Gündüz", "Duman", "Acar",
    "Tekin", "Sari", "Bozkurt", "Ates", "Demirci", "Uysal", "Bilgin", "Aktas",
    "Karaca", "Turan", "Ünal", "Sezer", "Toprak", "Basaran", "Sönmez", "Işik",
    "Balci", "Ergün", "Yalçin", "Altun", "Coskun", "Güneş", "Tas", "Avci",
]

DE_FIRST_M = [
    "Lukas", "Jonas", "Maximilian", "Felix", "Paul", "Leon", "Elias", "Niklas",
    "Tobias", "Sebastian", "Andreas", "Michael", "Thomas", "Stefan", "Christian",
    "Matthias", "Jan", "Marcel", "Dennis", "Kai", "Sven", "Torben", "Hendrik",
    "Malte", "Jens", "Bjoern", "Frank", "Dirk", "Holger", "Uwe",
]

DE_FIRST_F = [
    "Anna", "Lena", "Sophie", "Marie", "Julia", "Laura", "Sarah", "Katharina",
    "Christina", "Nicole", "Sandra", "Claudia", "Petra", "Susanne", "Birgit",
    "Kerstin", "Antje", "Meike", "Silke", "Franziska", "Johanna", "Nina",
]

DE_LAST = [
    "Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner",
    "Becker", "Schulz", "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter",
    "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann", "Braun",
    "Krüger", "Hofmann", "Hartmann", "Lange", "Schmitt", "Werner", "Krause",
    "Meier", "Lehmann", "Petersen", "Jansen", "Boysen", "Timmermann", "Ahrens",
]

# ---------------------------------------------------------------- places ----

# (city, region/state, country_name, iso2, phone_cc, currency, in_eu)
EU_LOCATIONS = [
    ("Hamburg", "Hamburg", "Germany", "DE", "49", "EUR", True),
    ("Bremen", "Bremen", "Germany", "DE", "49", "EUR", True),
    ("Hannover", "Lower Saxony", "Germany", "DE", "49", "EUR", True),
    ("Bielefeld", "North Rhine-Westphalia", "Germany", "DE", "49", "EUR", True),
    ("Dortmund", "North Rhine-Westphalia", "Germany", "DE", "49", "EUR", True),
    ("Düsseldorf", "North Rhine-Westphalia", "Germany", "DE", "49", "EUR", True),
    ("Solingen", "North Rhine-Westphalia", "Germany", "DE", "49", "EUR", True),
    ("Stuttgart", "Baden-Württemberg", "Germany", "DE", "49", "EUR", True),
    ("Villingen-Schwenningen", "Baden-Württemberg", "Germany", "DE", "49", "EUR", True),
    ("Nürnberg", "Bavaria", "Germany", "DE", "49", "EUR", True),
    ("Augsburg", "Bavaria", "Germany", "DE", "49", "EUR", True),
    ("Chemnitz", "Saxony", "Germany", "DE", "49", "EUR", True),
    ("Leipzig", "Saxony", "Germany", "DE", "49", "EUR", True),
    ("Wien", "Vienna", "Austria", "AT", "43", "EUR", True),
    ("Linz", "Upper Austria", "Austria", "AT", "43", "EUR", True),
    ("Graz", "Styria", "Austria", "AT", "43", "EUR", True),
    ("Zürich", "Zürich", "Switzerland", "CH", "41", "CHF", False),
    ("Biel/Bienne", "Bern", "Switzerland", "CH", "41", "CHF", False),
    ("Milano", "Lombardy", "Italy", "IT", "39", "EUR", True),
    ("Brescia", "Lombardy", "Italy", "IT", "39", "EUR", True),
    ("Bergamo", "Lombardy", "Italy", "IT", "39", "EUR", True),
    ("Torino", "Piedmont", "Italy", "IT", "39", "EUR", True),
    ("Bologna", "Emilia-Romagna", "Italy", "IT", "39", "EUR", True),
    ("Vicenza", "Veneto", "Italy", "IT", "39", "EUR", True),
    ("Barcelona", "Catalonia", "Spain", "ES", "34", "EUR", True),
    ("Bilbao", "Basque Country", "Spain", "ES", "34", "EUR", True),
    ("Zaragoza", "Aragon", "Spain", "ES", "34", "EUR", True),
    ("Vigo", "Galicia", "Spain", "ES", "34", "EUR", True),
    ("Porto", "Porto", "Portugal", "PT", "351", "EUR", True),
    ("Aveiro", "Aveiro", "Portugal", "PT", "351", "EUR", True),
    ("Lyon", "Auvergne-Rhône-Alpes", "France", "FR", "33", "EUR", True),
    ("Cluses", "Auvergne-Rhône-Alpes", "France", "FR", "33", "EUR", True),
    ("Lille", "Hauts-de-France", "France", "FR", "33", "EUR", True),
    ("Toulouse", "Occitanie", "France", "FR", "33", "EUR", True),
    ("Eindhoven", "North Brabant", "Netherlands", "NL", "31", "EUR", True),
    ("Rotterdam", "South Holland", "Netherlands", "NL", "31", "EUR", True),
    ("Enschede", "Overijssel", "Netherlands", "NL", "31", "EUR", True),
    ("Antwerpen", "Flanders", "Belgium", "BE", "32", "EUR", True),
    ("Liège", "Wallonia", "Belgium", "BE", "32", "EUR", True),
    ("Kraków", "Lesser Poland", "Poland", "PL", "48", "PLN", True),
    ("Katowice", "Silesia", "Poland", "PL", "48", "PLN", True),
    ("Poznań", "Greater Poland", "Poland", "PL", "48", "PLN", True),
    ("Wrocław", "Lower Silesia", "Poland", "PL", "48", "PLN", True),
    ("Brno", "South Moravia", "Czechia", "CZ", "420", "CZK", True),
    ("Plzeň", "Plzeň Region", "Czechia", "CZ", "420", "CZK", True),
    ("Ostrava", "Moravian-Silesian", "Czechia", "CZ", "420", "CZK", True),
    ("Košice", "Košice Region", "Slovakia", "SK", "421", "EUR", True),
    ("Žilina", "Žilina Region", "Slovakia", "SK", "421", "EUR", True),
    ("Győr", "Győr-Moson-Sopron", "Hungary", "HU", "36", "HUF", True),
    ("Miskolc", "Borsod-Abaúj-Zemplén", "Hungary", "HU", "36", "HUF", True),
    ("Cluj-Napoca", "Cluj", "Romania", "RO", "40", "RON", True),
    ("Brașov", "Brașov", "Romania", "RO", "40", "RON", True),
    ("Timișoara", "Timiș", "Romania", "RO", "40", "RON", True),
    ("Plovdiv", "Plovdiv", "Bulgaria", "BG", "359", "EUR", True),
    ("Sofia", "Sofia-City", "Bulgaria", "BG", "359", "EUR", True),
    ("Ljubljana", "Central Slovenia", "Slovenia", "SI", "386", "EUR", True),
    ("Zagreb", "Zagreb", "Croatia", "HR", "385", "EUR", True),
    ("Odense", "Southern Denmark", "Denmark", "DK", "45", "DKK", True),
    ("Aarhus", "Central Denmark", "Denmark", "DK", "45", "DKK", True),
    ("Göteborg", "Västra Götaland", "Sweden", "SE", "46", "SEK", True),
    ("Jönköping", "Jönköping", "Sweden", "SE", "46", "SEK", True),
    ("Tampere", "Pirkanmaa", "Finland", "FI", "358", "EUR", True),
    ("Kongsberg", "Buskerud", "Norway", "NO", "47", "NOK", False),
    ("Sheffield", "South Yorkshire", "United Kingdom", "GB", "44", "GBP", False),
    ("Birmingham", "West Midlands", "United Kingdom", "GB", "44", "GBP", False),
    ("Leeds", "West Yorkshire", "United Kingdom", "GB", "44", "GBP", False),
    ("Thessaloniki", "Central Macedonia", "Greece", "GR", "30", "EUR", True),
]

TR_LOCATIONS = [
    ("İstanbul", "İstanbul", "Türkiye", "TR", "90", "TRY", False),
    ("Tuzla", "İstanbul", "Türkiye", "TR", "90", "TRY", False),
    ("Gebze", "Kocaeli", "Türkiye", "TR", "90", "TRY", False),
    ("İzmit", "Kocaeli", "Türkiye", "TR", "90", "TRY", False),
    ("Bursa", "Bursa", "Türkiye", "TR", "90", "TRY", False),
    ("İnegöl", "Bursa", "Türkiye", "TR", "90", "TRY", False),
    ("İzmir", "İzmir", "Türkiye", "TR", "90", "TRY", False),
    ("Manisa", "Manisa", "Türkiye", "TR", "90", "TRY", False),
    ("Ankara", "Ankara", "Türkiye", "TR", "90", "TRY", False),
    ("Konya", "Konya", "Türkiye", "TR", "90", "TRY", False),
    ("Kayseri", "Kayseri", "Türkiye", "TR", "90", "TRY", False),
    ("Eskişehir", "Eskişehir", "Türkiye", "TR", "90", "TRY", False),
    ("Denizli", "Denizli", "Türkiye", "TR", "90", "TRY", False),
    ("Gaziantep", "Gaziantep", "Türkiye", "TR", "90", "TRY", False),
    ("Adana", "Adana", "Türkiye", "TR", "90", "TRY", False),
    ("Sakarya", "Sakarya", "Türkiye", "TR", "90", "TRY", False),
    ("Çerkezköy", "Tekirdağ", "Türkiye", "TR", "90", "TRY", False),
    ("Karabük", "Karabük", "Türkiye", "TR", "90", "TRY", False),
    ("İskenderun", "Hatay", "Türkiye", "TR", "90", "TRY", False),
]

DE_STREETS = [
    "Industriestraße", "Hafenstraße", "Werftstraße", "Am Stahlwerk", "Gewerbering",
    "Maschinenweg", "Hansastraße", "Elbchaussee", "Billbrookdeich", "Peutestraße",
    "Rugenbergener Weg", "Schlachthofstraße", "Zum Hafenplatz", "Stahltwiete",
    "Große Elbstraße", "Veddeler Damm", "Reiherstiegstraße", "Kranstraße",
]

TR_STREETS = [
    "Organize Sanayi Bölgesi 3. Cadde", "Tersaneler Caddesi", "Sanayi Mahallesi 12. Sokak",
    "Aydınlı Yolu Caddesi", "Deri Organize Sanayi Bölgesi", "İstasyon Caddesi",
    "Fabrikalar Caddesi", "Demirciler Sitesi", "Makine İhtisas OSB 5. Cadde",
    "Atatürk Bulvarı", "Çelik Sokak", "Torna Caddesi",
]

EU_STREETS = [
    "Industrieweg", "Rue de l'Industrie", "Via dell'Industria", "Polígono Industrial",
    "Ulica Przemysłowa", "Průmyslová", "Ipari út", "Strada Industriilor",
    "Industrivej", "Verkstadsgatan", "Bahnhofstrasse", "Werkstrasse",
    "Zona Industriale", "Calle del Metal", "Chemin des Ateliers", "Steelworks Road",
    "Foundry Lane", "Machine Park Avenue",
]

# ------------------------------------------------------------- accessors ----


def person(rng, locale: str = "tr"):
    """Return (first_name, last_name) for a locale ('tr' | 'de')."""
    if locale == "de":
        first = rng.choice(DE_FIRST_M) if rng.chance(0.72) else rng.choice(DE_FIRST_F)
        return first, rng.choice(DE_LAST)
    first = rng.choice(TR_FIRST_M) if rng.chance(0.75) else rng.choice(TR_FIRST_F)
    return first, rng.choice(TR_LAST)


def location(rng, pool):
    """Pick a (city, region, country, iso2, phone_cc, currency, in_eu) tuple."""
    return rng.choice(pool)


def street_for(rng, iso2: str) -> str:
    if iso2 == "DE":
        base = rng.choice(DE_STREETS)
    elif iso2 == "TR":
        base = rng.choice(TR_STREETS)
    else:
        base = rng.choice(EU_STREETS)
    return f"{base} {rng.randint(1, 199)}"


def postcode_for(rng, iso2: str) -> str:
    if iso2 in ("DE", "IT", "ES", "FR", "FI"):
        return f"{rng.randint(10000, 99999)}"
    if iso2 == "TR":
        return f"{rng.randint(1, 81):02d}{rng.randint(100, 999)}"
    if iso2 == "NL":
        return f"{rng.randint(1000, 9999)} {chr(rng.randint(65,90))}{chr(rng.randint(65,90))}"
    if iso2 == "PL":
        return f"{rng.randint(10,99)}-{rng.randint(100,999)}"
    if iso2 == "CZ":
        return f"{rng.randint(100,799)} {rng.randint(10,99)}"
    if iso2 == "GB":
        return f"{chr(rng.randint(65,90))}{chr(rng.randint(65,90))}{rng.randint(1,20)} {rng.randint(1,9)}{chr(rng.randint(65,90))}{chr(rng.randint(65,90))}"
    if iso2 in ("SE", "NO"):
        return f"{rng.randint(100,999)} {rng.randint(10,99)}"
    if iso2 == "AT":
        return f"{rng.randint(1000, 9999)}"
    return f"{rng.randint(1000, 99999)}"


def phone_for(rng, phone_cc: str) -> str:
    return f"+{phone_cc} {rng.randint(100, 999)} {rng.randint(1000000, 9999999)}"


# European / Turkish company-name synthesis, for the long tail beyond the names
# the seed file supplies by hand.
INTL_HEADS = [
    "Nord", "Elbe", "Rhein", "Alpen", "Vulkan", "Ferro", "Titan", "Kappa", "Delta",
    "Omega", "Meta", "Mikro", "Makro", "Präzision", "Stahl", "Metall", "Werk", "Technik",
    "Anadolu", "Marmara", "Ege", "Toros", "Özkan", "Demir", "Çelik", "Torna", "Tezgah",
    "Mercur", "Vento", "Aurora", "Baltica", "Silesia", "Vitesse", "Acier", "Metaal",
    "Acciaio", "Hierro", "Vista", "Primo", "Nova", "Orion", "Helix", "Vector", "Axis",
    "Kronos", "Atlas", "Boreal", "Baltic", "Adriatic", "Danube", "Vistula", "Hanse",
]
INTL_TAILS = [
    "Zerspanung", "Metallbau", "Maschinenbau", "Werkzeugbau", "Präzisionstechnik",
    "Feinmechanik", "Stahlbau", "Antriebstechnik", "Fertigung", "Industrietechnik",
    "Makina", "Metal", "Endüstri", "Kalıp", "Otomotiv", "Döküm", "Fabrikasyon",
    "Machining", "Engineering", "Precision", "Toolworks", "Mechanics", "Fabrication",
    "Metalworks", "Industries", "Systems", "Components", "Automation", "Hydraulics",
    "Meccanica", "Meccanotecnica", "Metaaltechniek", "Mécanique", "Usinage",
    "Obróbka", "Narzędzia", "Kovoobrábění", "Gépgyár", "Mecanica", "Verkstad",
]
# Legal form by country. A synthesized name only gets its suffix once the
# company's country is known, otherwise the data ends up full of Turkish firms
# called "S.L." and Norwegian ones called "GmbH & Co. KG".
COUNTRY_SUFFIXES = {
    "DE": ["GmbH", "GmbH & Co. KG", "AG", "GmbH"],
    "AT": ["GmbH", "AG"],
    "CH": ["AG", "SA"],
    "TR": ["A.Ş.", "Ltd. Şti.", "San. ve Tic. A.Ş."],
    "PL": ["Sp. z o.o.", "S.A."],
    "CZ": ["s.r.o.", "a.s."],
    "SK": ["s.r.o.", "a.s."],
    "HU": ["Kft.", "Zrt."],
    "RO": ["S.R.L.", "S.A."],
    "BG": ["EOOD", "AD"],
    "SI": ["d.o.o."],
    "HR": ["d.o.o."],
    "IT": ["S.r.l.", "S.p.A."],
    "ES": ["S.L.", "S.A."],
    "PT": ["Lda.", "S.A."],
    "FR": ["SAS", "SARL"],
    "NL": ["B.V."],
    "BE": ["N.V.", "SA"],
    "GB": ["Ltd", "Limited"],
    "SE": ["AB"],
    "DK": ["A/S"],
    "NO": ["AS"],
    "FI": ["Oy"],
    "GR": ["S.A."],
}


def company_suffix(rng, iso2: str) -> str:
    return rng.choice(COUNTRY_SUFFIXES.get(iso2, ["Ltd"]))


def extend_company_names_intl(rng, base: list, target: int) -> list:
    """Return ``target`` unique company names. Hand-written ``base`` names come
    first complete with their legal form; synthesized names are returned WITHOUT
    a legal suffix so the caller can attach one that matches the country it
    assigns (see ``company_suffix``)."""
    out = list(dict.fromkeys(base))
    seen = set(out)
    guard = 0
    while len(out) < target and guard < target * 60:
        guard += 1
        name = f"{rng.choice(INTL_HEADS)} {rng.choice(INTL_TAILS)}"
        if name not in seen:
            seen.add(name)
            out.append(name)
    i = 2
    while len(out) < target:
        cand = f"{rng.choice(INTL_HEADS)}-{rng.choice(INTL_TAILS)} {i}"
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
        i += 1
    return out[:target]


# --------------------------------------------------- yakın pazar ihracatı ----
# Gaziantep merkezli bir yan sanayi üreticisinin fiilen sattığı yakın pazarlar:
# Ortadoğu, Kafkasya, Orta Asya ve Balkanlar. (şehir, bölge, ülke, iso2,
# telefon kodu, para birimi, AB üyesi mi)
NEAR_EXPORT_LOCATIONS = [
    ("Bağdat", "Bağdat", "Irak", "IQ", "964", "USD", False),
    ("Erbil", "Erbil", "Irak", "IQ", "964", "USD", False),
    ("Basra", "Basra", "Irak", "IQ", "964", "USD", False),
    ("Tebriz", "Doğu Azerbaycan", "İran", "IR", "98", "USD", False),
    ("Tahran", "Tahran", "İran", "IR", "98", "USD", False),
    ("Bakü", "Bakü", "Azerbaycan", "AZ", "994", "USD", False),
    ("Gence", "Gence", "Azerbaycan", "AZ", "994", "USD", False),
    ("Tiflis", "Tiflis", "Gürcistan", "GE", "995", "USD", False),
    ("Kutaisi", "İmereti", "Gürcistan", "GE", "995", "USD", False),
    ("Kahire", "Kahire", "Mısır", "EG", "20", "USD", False),
    ("İskenderiye", "İskenderiye", "Mısır", "EG", "20", "USD", False),
    ("Amman", "Amman", "Ürdün", "JO", "962", "USD", False),
    ("Riyad", "Riyad", "Suudi Arabistan", "SA", "966", "USD", False),
    ("Dammam", "Doğu Bölgesi", "Suudi Arabistan", "SA", "966", "USD", False),
    ("Dubai", "Dubai", "Birleşik Arap Emirlikleri", "AE", "971", "USD", False),
    ("Şarja", "Şarja", "Birleşik Arap Emirlikleri", "AE", "971", "USD", False),
    ("Doha", "Doha", "Katar", "QA", "974", "USD", False),
    ("Kuveyt", "Kuveyt", "Kuveyt", "KW", "965", "USD", False),
    ("Taşkent", "Taşkent", "Özbekistan", "UZ", "998", "USD", False),
    ("Almatı", "Almatı", "Kazakistan", "KZ", "7", "USD", False),
    ("Astana", "Astana", "Kazakistan", "KZ", "7", "USD", False),
    ("Aşkabat", "Aşkabat", "Türkmenistan", "TM", "993", "USD", False),
    ("Üsküp", "Üsküp", "Kuzey Makedonya", "MK", "389", "EUR", False),
    ("Belgrad", "Belgrad", "Sırbistan", "RS", "381", "EUR", False),
    ("Saraybosna", "Saraybosna", "Bosna-Hersek", "BA", "387", "EUR", False),
    ("Tiran", "Tiran", "Arnavutluk", "AL", "355", "EUR", False),
    ("Priştine", "Priştine", "Kosova", "XK", "383", "EUR", False),
    ("Kazablanka", "Kazablanka", "Fas", "MA", "212", "EUR", False),
    ("Tunus", "Tunus", "Tunus", "TN", "216", "EUR", False),
    ("Cezayir", "Cezayir", "Cezayir", "DZ", "213", "USD", False),
    ("Trablus", "Trablus", "Libya", "LY", "218", "USD", False),
]

NEAR_EXPORT_SUFFIXES = {
    "IQ": ["Co. Ltd", "General Trading Co."], "IR": ["Co.", "Industrial Co."],
    "AZ": ["MMC", "ASC"], "GE": ["LLC", "Ltd"], "EG": ["S.A.E.", "Co."],
    "JO": ["LLC", "Co."], "SA": ["Co. Ltd", "LLC"], "AE": ["LLC", "FZE", "FZC"],
    "QA": ["W.L.L.", "Co."], "KW": ["W.L.L.", "Co."], "UZ": ["MChJ", "AJ"],
    "KZ": ["TOO", "AO"], "TM": ["HJ"], "MK": ["DOOEL", "DOO"], "RS": ["d.o.o."],
    "BA": ["d.o.o."], "AL": ["Sh.p.k."], "XK": ["Sh.p.k."], "MA": ["S.A.R.L.", "S.A."],
    "TN": ["SARL", "SA"], "DZ": ["SARL", "SPA"], "LY": ["Co."],
}

# Gaziantep ve çevresi organize sanayi adresleri
GAZIANTEP_STREETS = [
    "1. Organize Sanayi Bölgesi 83201 Nolu Cadde",
    "2. Organize Sanayi Bölgesi 83409 Nolu Cadde",
    "3. Organize Sanayi Bölgesi 83512 Nolu Cadde",
    "4. Organize Sanayi Bölgesi 83620 Nolu Cadde",
    "5. Organize Sanayi Bölgesi 83715 Nolu Cadde",
    "Başpınar Organize Sanayi Bölgesi 8. Cadde",
    "Küçük Sanayi Sitesi 12. Blok",
    "Nizip Organize Sanayi Bölgesi 3. Cadde",
    "İnönü Caddesi", "Ali Fuat Cebesoy Bulvarı", "Şehitkamil Sanayi Caddesi",
    "Oğuzeli Yolu 7. km", "Havalimanı Yolu 12. km",
]

# Türk sanayi firması adı üretimi (elle yazılan listeden sonraki uzun kuyruk).
TR_CO_HEADS = [
    "Anadolu", "Toros", "Ege", "Marmara", "Fırat", "Dicle", "Gaziantep", "Antep",
    "Şahinbey", "Nizip", "Zeugma", "Kilis", "Maraş", "Adıyaman", "Urfa", "Malatya",
    "Öz", "Öztürk", "Demir", "Çelik", "Yıldız", "Yılmaz", "Kaya", "Aslan", "Kartal",
    "Şahin", "Doğan", "Bozkurt", "Ceylan", "Akın", "Güven", "Birlik", "Başak",
    "Sürat", "Hassas", "Mikro", "Metro", "Nova", "Star", "Teknik", "Endüstri",
    "Mert", "Emin", "Sadık", "Berk", "Tuna", "Efe", "Alp", "Ata", "Kudret",
    "Volkan", "Ertaş", "Karaca", "Uğur", "Umut", "Zafer", "Gürsoy", "Erbay",
]
TR_CO_TAILS = [
    "Makina", "Metal", "Otomotiv", "Endüstri", "Mühendislik", "Talaşlı İmalat",
    "Hassas İşleme", "Kalıp", "Döküm", "Dövme", "Hidrolik", "Pnömatik", "Rulman",
    "Bağlantı Elemanları", "Sac Metal", "Isıl İşlem", "Kaplama", "Otomat Torna",
    "CNC", "Teknik Malzeme", "Sanayi", "Fabrikasyon", "Metal İşleme", "Vana",
    "Redüktör", "Pompa", "Aktarma Organları", "Şanzıman", "Tarım Makinaları",
    "Beyaz Eşya Parçaları", "Yedek Parça", "Takım", "Konnektör", "Contalar",
]
TR_CO_SUFFIXES = [
    "San. ve Tic. A.Ş.", "San. ve Tic. Ltd. Şti.", "A.Ş.", "Ltd. Şti.",
    "Sanayi ve Ticaret A.Ş.", "Otomotiv San. Tic. A.Ş.", "Makina San. Tic. Ltd. Şti.",
]


def tr_company_suffix(rng) -> str:
    return rng.weighted(TR_CO_SUFFIXES, [30, 26, 10, 10, 10, 7, 7])


def extend_company_names_tr(rng, base: list, target: int) -> list:
    """``target`` adet benzersiz Türk sanayi firması adı döndürür. Elle yazılan
    adlar hukuki ekiyle birlikte gelir; üretilenlere ek burada takılır."""
    out = list(dict.fromkeys(base))
    seen = set(out)
    guard = 0
    while len(out) < target and guard < target * 80:
        guard += 1
        name = f"{rng.choice(TR_CO_HEADS)} {rng.choice(TR_CO_TAILS)} {tr_company_suffix(rng)}"
        if name not in seen:
            seen.add(name)
            out.append(name)
    i = 2
    while len(out) < target:
        cand = (f"{rng.choice(TR_CO_HEADS)}-{rng.choice(TR_CO_TAILS)} {i} "
                f"{tr_company_suffix(rng)}")
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
        i += 1
    return out[:target]


def near_export_suffix(rng, iso2: str) -> str:
    return rng.choice(NEAR_EXPORT_SUFFIXES.get(iso2, ["Co. Ltd"]))
