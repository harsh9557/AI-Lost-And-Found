"""Text + perceptual-image matching helpers for AI Lost & Found."""
import os
import re
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
import imagehash
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _text(item):
    fields = [item.get("item_name", ""), item.get("description", ""), item.get("color", ""), item.get("location", "")]
    return " ".join(re.sub(r"\s+", " ", str(v or "")).strip().lower() for v in fields).strip()


def text_match(lost_item, found_item):
    a, b = _text(lost_item), _text(found_item)
    if not a or not b:
        return 0.0
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True).fit_transform([a, b])
        return round(float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0]) * 100, 2)
    except ValueError:  # empty vocabulary, e.g. punctuation-only text
        return 0.0


def image_match(lost_photo, found_photo):
    if not lost_photo or not found_photo or not os.path.isfile(lost_photo) or not os.path.isfile(found_photo):
        return 0.0
    try:
        with Image.open(lost_photo) as im1, Image.open(found_photo) as im2:
            im1 = ImageOps.exif_transpose(im1).convert("RGB")
            im2 = ImageOps.exif_transpose(im2).convert("RGB")
            h1, h2 = imagehash.phash(im1, hash_size=8), imagehash.phash(im2, hash_size=8)
        return round(max(0.0, 100.0 * (1.0 - (h1 - h2) / 64.0)), 2)
    except (OSError, ValueError, UnidentifiedImageError):
        return 0.0


def calculate_match(lost_item, found_item):
    """Return score from 0-100. Missing photos do not penalize text-only matches."""
    t_score = text_match(lost_item, found_item)
    i_score = image_match(lost_item.get("photo", ""), found_item.get("photo", ""))
    has_two_images = bool(lost_item.get("photo") and found_item.get("photo") and
                          os.path.isfile(lost_item.get("photo", "")) and os.path.isfile(found_item.get("photo", "")))
    final = (0.75 * t_score + 0.25 * i_score) if has_two_images else t_score
    return round(final, 2)
