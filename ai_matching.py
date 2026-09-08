from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from PIL import Image
import imagehash
import os
from io import BytesIO
from urllib.request import urlopen


def text_match(lost_item, found_item):

    lost_text = " ".join([
        str(lost_item.get("item_name", "")),
        str(lost_item.get("description", "")),
        str(lost_item.get("color", "")),
        str(lost_item.get("location", ""))
    ]).lower()

    found_text = " ".join([
        str(found_item.get("item_name", "")),
        str(found_item.get("description", "")),
        str(found_item.get("color", "")),
        str(found_item.get("location", ""))
    ]).lower()

    if not lost_text.strip() or not found_text.strip():
        return 0

    try:
        vectorizer = TfidfVectorizer()

        vectors = vectorizer.fit_transform([
            lost_text,
            found_text
        ])

        similarity = cosine_similarity(
            vectors[0:1],
            vectors[1:2]
        )[0][0]

        return round(similarity * 100, 2)

    except Exception:
        return 0


def image_match(lost_photo, found_photo):

    if not lost_photo or not found_photo:
        return 0

    try:

        def load_image(photo):
            if str(photo).startswith(("http://", "https://")):
                data = urlopen(str(photo), timeout=10).read()
                return Image.open(BytesIO(data))

            if not os.path.exists(photo):
                return None

            return Image.open(photo)

        lost_image = load_image(lost_photo)
        found_image = load_image(found_photo)

        if lost_image is None or found_image is None:
            return 0

        lost_hash = imagehash.phash(lost_image)
        found_hash = imagehash.phash(found_image)

        difference = lost_hash - found_hash

        similarity = max(
            0,
            100 - (difference * 100 / 64)
        )

        return round(similarity, 2)

    except Exception:
        return 0


def calculate_match(lost_item, found_item):

    text_score = text_match(
        lost_item,
        found_item
    )

    image_score = image_match(
        lost_item.get("photo", ""),
        found_item.get("photo", "")
    )

    final_score = (
        text_score * 0.7
        +
        image_score * 0.3
    )

    return round(final_score, 2)