"""Curated name pools (stdlib-only replacement for Faker).

The LLM supplies the *interesting* on-industry names (company identity, product
names, a pool of customer/vendor company names). This module covers the
high-volume, low-creativity needs: people names, cities, streets, and
extending a capped company-name pool into a long tail when more uniques are
needed than the LLM provided.
"""
from __future__ import annotations

from .util import Rng

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Amy", "Gary", "Kathleen",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Nicole", "Scott", "Samantha", "Brandon", "Katherine",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
]

CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"), ("Houston", "TX"),
    ("Phoenix", "AZ"), ("Philadelphia", "PA"), ("San Antonio", "TX"), ("San Diego", "CA"),
    ("Dallas", "TX"), ("Austin", "TX"), ("San Jose", "CA"), ("Columbus", "OH"),
    ("Charlotte", "NC"), ("Indianapolis", "IN"), ("Seattle", "WA"), ("Denver", "CO"),
    ("Boston", "MA"), ("Nashville", "TN"), ("Portland", "OR"), ("Atlanta", "GA"),
    ("Detroit", "MI"), ("Memphis", "TN"), ("Louisville", "KY"), ("Milwaukee", "WI"),
    ("Kansas City", "MO"), ("Cleveland", "OH"), ("Minneapolis", "MN"), ("Tampa", "FL"),
]

STREETS = [
    "Main St", "Oak Ave", "Maple Dr", "Industrial Pkwy", "Commerce Blvd", "Market St",
    "Washington Ave", "Park Rd", "Lincoln Way", "Cedar Ln", "Lakeview Dr", "Pine St",
    "Riverside Dr", "Franklin Ave", "Madison St", "Enterprise Ct", "Logistics Way",
]

COMPANY_SUFFIXES = ["Inc", "LLC", "Corp", "Co", "Group", "Holdings", "Partners", "Industries"]
COMPANY_HEADS = [
    "Summit", "Pioneer", "Vertex", "Apex", "Keystone", "Horizon", "Cascade", "Atlas",
    "Beacon", "Sterling", "Crestline", "Meridian", "Ironwood", "Granite", "Bluepeak",
    "Northstar", "Evergreen", "Redwood", "Sentinel", "Vanguard", "Cobalt", "Falcon",
    "Harbor", "Lakeside", "Mesa", "Pinnacle", "Quartz", "Riverstone", "Tradewind", "Union",
]
COMPANY_TAILS = [
    "Supply", "Trading", "Distribution", "Logistics", "Wholesale", "Solutions",
    "Enterprises", "Mercantile", "Commerce", "Provisions", "Outfitters", "Brands",
    "Goods", "Markets", "Retail", "Partners", "Systems", "Works",
]


def person(rng: Rng):
    fn = rng.choice(FIRST_NAMES)
    ln = rng.choice(LAST_NAMES)
    return fn, ln


def email_for(first: str, last: str, domain: str, n: int = 0) -> str:
    base = f"{first}.{last}".lower().replace(" ", "")
    if n:
        base = f"{base}{n}"
    return f"{base}@{domain}"


def slug_domain(name: str) -> str:
    s = "".join(c for c in name.lower() if c.isalnum() or c == " ").strip()
    s = s.split()
    return (s[0] if s else "company") + ".example.com"


def address(rng: Rng):
    city, state = rng.choice(CITIES)
    num = rng.randint(10, 9999)
    street = rng.choice(STREETS)
    return f"{num} {street}", city, state, "USA"


def extend_company_names(rng: Rng, base: list[str], target: int) -> list[str]:
    """Return ``target`` unique company names, reusing LLM-provided ``base``
    first and synthesizing the long tail deterministically."""
    out = list(dict.fromkeys(base))  # dedupe, preserve order
    seen = set(out)
    guard = 0
    while len(out) < target and guard < target * 50:
        guard += 1
        name = f"{rng.choice(COMPANY_HEADS)} {rng.choice(COMPANY_TAILS)} {rng.choice(COMPANY_SUFFIXES)}"
        if name not in seen:
            seen.add(name)
            out.append(name)
    # Last resort: numeric suffixes to guarantee uniqueness.
    i = 2
    while len(out) < target:
        cand = f"{rng.choice(COMPANY_HEADS)} {rng.choice(COMPANY_TAILS)} {i}"
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
        i += 1
    return out[:target]
