import os

from django.conf import settings
from PIL import Image, ImageOps

THUMBNAIL_MAX_SIZE = (1600, 1600)
THUMBNAIL_JPEG_QUALITY = 85


def compress_image(infile, outfile='', kb=40, quality=80):
    """不改变图片尺寸压缩到指定大小
    :param infile: 压缩源文件
    :param outfile: 压缩文件保存地址
    :param kb: 压缩目标, KB
    :param step: 每次调整的压缩比率
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    o_size = os.path.getsize(infile)/1024
    if o_size <= kb:
        return infile
    if outfile == '':
        path, end = infile.split('.')
        outfile = path + '_compressed.' + end
    im = Image.open(infile)
    im.save(outfile, quality=quality)
    while os.path.getsize(outfile) / 1024 > kb:
        imx = Image.open(outfile)
        # Resize the image using the same aspect ratio to reduce the file size
        width, height = imx.size
        new_width = int(width * 0.9)  # You can adjust the scaling factor
        new_height = int(height * 0.9)
        imx = imx.resize((new_width, new_height), Image.ANTIALIAS)
        imx.save(outfile, quality=quality)
        # quality -= step

    return outfile, os.path.getsize(outfile) / 1024


def get_media_abs_path(media_path: str) -> str:
    if not media_path:
        return ""
    normalized_path = media_path.replace("\\", "/")
    if normalized_path.startswith(settings.MEDIA_URL):
        normalized_path = normalized_path[len(settings.MEDIA_URL):]
    normalized_path = normalized_path.lstrip("/")
    return os.path.join(settings.BASE_DIR, "media", normalized_path)


def build_small_media_path(media_path: str, use_png: bool = False) -> str:
    normalized_path = media_path.replace("\\", "/")
    directory, filename = os.path.split(normalized_path)
    stem, _ext = os.path.splitext(filename)
    suffix = ".png" if use_png else ".jpg"
    return f"{directory}/{stem}_small{suffix}"


def _save_thumbnail(source_path: str, target_path: str):
    with Image.open(source_path) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail(THUMBNAIL_MAX_SIZE)
        has_alpha = "A" in img.getbands() or img.mode in ("LA", "RGBA", "PA")
        save_as_png = has_alpha
        save_media_path = build_small_media_path(target_path, use_png=save_as_png)
        save_abs_path = get_media_abs_path(save_media_path)
        os.makedirs(os.path.dirname(save_abs_path), exist_ok=True)

        if save_as_png:
            img.save(save_abs_path, format="PNG", optimize=True)
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(save_abs_path, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY, optimize=True)
        return save_media_path


def ensure_small_image(file_obj):
    if not file_obj:
        return getattr(file_obj, "path", "")
    file_type = getattr(file_obj, "type", None)
    image_type = getattr(file_obj, "FILE_TYPE_PIC", 40)
    if str(file_type) != str(image_type):
        return getattr(file_obj, "path", "")

    small_path = getattr(file_obj, "small_path", "")
    if small_path and os.path.exists(get_media_abs_path(small_path)):
        return small_path

    origin_path = getattr(file_obj, "path", "")
    origin_abs_path = get_media_abs_path(origin_path)
    if not origin_path or not os.path.exists(origin_abs_path):
        return origin_path

    generated_small_path = _save_thumbnail(origin_abs_path, origin_path)
    if generated_small_path != small_path:
        file_obj.small_path = generated_small_path
        file_obj.save(update_fields=["small_path"])
    return generated_small_path


def ensure_small_image_by_path(media_path: str) -> str:
    if not media_path:
        return media_path

    try:
        from apps.system.models import File
    except Exception:
        return media_path

    file_obj = File.objects.filter(path=media_path).first()
    if file_obj:
        return ensure_small_image(file_obj)

    origin_abs_path = get_media_abs_path(media_path)
    if not os.path.exists(origin_abs_path):
        return media_path
    return _save_thumbnail(origin_abs_path, media_path)
