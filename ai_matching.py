from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from PIL import Image
import imagehash
import os


def _clean(value):
    return str(value or "").strip().lower()


def _text_similarity(text1, text2):
    text1 = _clean(text1)
    text2 = _clean(text2)

    if not text1 or not text2:
        return 0.0

    if text1 == text2:
        return 100.0

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2)
        )
        vectors = vectorizer.fit_transform([text1, text2])

        if vectors.shape[1] == 0:
            return 0.0

        score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0] * 100
        return round(float(score), 2)
    except (ValueError, TypeError):
        return 0.0


def text_match(lost_item, found_item):
    """
    Text score uses separate fields so an exact color/location
    can contribute independently instead of being hidden inside
    one large text string.

    Weights:
    Item name   35%
    Description 25%
    Color       15%
    Location    25%
    """
    name_score = _text_similarity(
        lost_item.get("item_name"),
        found_item.get("item_name")
    )
    description_score = _text_similarity(
        lost_item.get("description"),
        found_item.get("description")
    )
    color_score = _text_similarity(
        lost_item.get("color"),
        found_item.get("color")
    )
    location_score = _text_similarity(
        lost_item.get("location"),
        found_item.get("location")
    )

    score = (
        name_score * 0.35
        + description_score * 0.25
        + color_score * 0.15
        + location_score * 0.25
    )

    return round(score, 2)


def image_match(lost_photo, found_photo):
    if not lost_photo or not found_photo:
        return 0.0

    if not os.path.exists(lost_photo) or not os.path.exists(found_photo):
        return 0.0

    try:
        with Image.open(lost_photo) as lost_image:
            with Image.open(found_photo) as found_image:
                lost_hash = imagehash.phash(lost_image)
                found_hash = imagehash.phash(found_image)

        difference = lost_hash - found_hash
        max_difference = lost_hash.hash.size

        if max_difference == 0:
            return 0.0

        similarity = max(
            0.0,
            100.0 - (difference * 100.0 / max_difference)
        )

        return round(similarity, 2)

    except (OSError, ValueError, TypeError):
        return 0.0


def calculate_match(lost_item, found_item):
    """
    Final score:
    Text = 70%
    Image = 30%
    """
    text_score = text_match(lost_item, found_item)
    image_score = image_match(
        lost_item.get("photo", ""),
        found_item.get("photo", "")
    )

    final_score = text_score * 0.70 + image_score * 0.30

    return round(final_score, 2)
