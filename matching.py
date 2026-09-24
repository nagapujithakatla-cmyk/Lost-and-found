from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean(value):
    return str(value or "").strip().lower()


def text_similarity(a, b):

    a = clean(a)
    b = clean(b)

    if not a or not b:
        return 0.0

    try:

        vectors = TfidfVectorizer(
            stop_words="english"
        ).fit_transform([
            a,
            b
        ])

        return float(
            cosine_similarity(
                vectors[0:1],
                vectors[1:2]
            )[0][0]
        )

    except ValueError:
        return 0.0


def exact_similarity(a, b):

    a = clean(a)
    b = clean(b)

    if not a or not b:
        return 0.0

    return 1.0 if a == b else 0.0


def partial_similarity(a, b):

    a = clean(a)
    b = clean(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    if a in b or b in a:
        return 0.8

    return text_similarity(a, b)


def date_similarity(d1, d2):

    if not d1 or not d2:
        return 0.5

    if isinstance(d1, str):
        try:
            d1 = date.fromisoformat(d1)
        except ValueError:
            return 0.5

    if isinstance(d2, str):
        try:
            d2 = date.fromisoformat(d2)
        except ValueError:
            return 0.5

    days = abs(
        (d1 - d2).days
    )

    if days == 0:
        return 1.0

    if days == 1:
        return 0.8

    if days <= 3:
        return 0.5

    return 0.0


def calculate_match_score(a, b):

    description = text_similarity(
        a.get("description"),
        b.get("description")
    )

    category = exact_similarity(
        a.get("category"),
        b.get("category")
    )

    brand = partial_similarity(
        a.get("brand"),
        b.get("brand")
    )

    color = partial_similarity(
        a.get("color"),
        b.get("color")
    )

    location = text_similarity(
        a.get("location"),
        b.get("location")
    )

    name = text_similarity(
        a.get("item_name"),
        b.get("item_name")
    )

    dt = date_similarity(
        a.get("item_date"),
        b.get("item_date")
    )

    score = (
        description * 0.30 +
        category * 0.15 +
        brand * 0.15 +
        color * 0.10 +
        location * 0.15 +
        name * 0.10 +
        dt * 0.05
    ) * 100

    details = {
        "description": round(description * 100, 1),
        "category": round(category * 100, 1),
        "brand": round(brand * 100, 1),
        "color": round(color * 100, 1),
        "location": round(location * 100, 1),
        "name": round(name * 100, 1),
        "date": round(dt * 100, 1)
    }

    return round(score, 2), details