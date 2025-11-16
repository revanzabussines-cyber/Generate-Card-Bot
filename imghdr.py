# imghdr.py - shim buat Python 3.13 ke atas
# Biar library yang masih pakai `import imghdr` nggak error.

from PIL import Image
import io

def what(file, h=None):
    """
    Mirip imghdr.what(filename, h=None)
    Balikin tipe gambar: 'jpeg', 'png', dll atau None kalau nggak ketebak.
    """
    try:
        if h is not None:
            img = Image.open(io.BytesIO(h))
        else:
            img = Image.open(file)

        fmt = img.format  # contoh: 'JPEG', 'PNG'
        return fmt.lower() if fmt else None
    except Exception:
        return None
