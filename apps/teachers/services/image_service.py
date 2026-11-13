
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from django.core.files.base import ContentFile
from rest_framework.exceptions import ValidationError


register_heif_opener()

MAX_IMAGE_SIZE = 5 * 1024 * 1024


def process_teacher_image(image_file):
    """
    HEIC/HEIF rasmlarini WebP formatiga o'tkazadi.
    JPEG, PNG va WebP rasmlarini original formatida qoldiradi.
    """

    if not image_file:
        return image_file

    image_file.seek(0)

    try:
        with Image.open(image_file) as image:
            if image.format not in {"HEIF", "HEIC"}:
                image_file.seek(0)
                return image_file

            image.load()

            # EXIF orientation bo'yicha rasmni to'g'rilash.
            image = ImageOps.exif_transpose(image)

            # Transparency mavjud bo'lsa saqlab qolish.
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")

            output = BytesIO()

            image.save(
                output,
                format="WEBP",
                quality=80,
                method=6,
            )

            if output.tell() > MAX_IMAGE_SIZE:
                raise ValidationError({
                    "photo": "Optimallashtirilgan rasm hajmi 5 MB dan oshdi."
                })

            original_name = Path(image_file.name).stem
            output_name = f"{original_name}.webp"

            return ContentFile(
                output.getvalue(),
                name=output_name,
            )


    except ValidationError:
        raise

    except (
            UnidentifiedImageError,
            Image.DecompressionBombError,
            OSError,
            ValueError,
            SyntaxError,
    ):
        raise ValidationError({
            "photo": "HEIC rasmni qayta ishlashda xatolik yuz berdi."
        })

    finally:
        image_file.seek(0)
