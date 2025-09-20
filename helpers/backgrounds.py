import io

# WARNING: not async!!
# WARNING: heavy workload!!
import pjsk_background_gen_PIL as pjsk_bg
from PIL import Image


def generate_backgrounds_resize_jacket(jacket_bytes: bytes):
    jacket_pil_image = Image.open(io.BytesIO(jacket_bytes))
    jacket_pil_image = jacket_pil_image.resize((1000, 1000)).convert("RGBA")
    v1 = pjsk_bg.render_v1(jacket_pil_image)
    v3 = pjsk_bg.render_v3(jacket_pil_image)
    v1_buffer = io.BytesIO()
    v1.save(v1_buffer, format="PNG")
    v1_bytes = v1_buffer.getvalue()
    v1_buffer.close()
    v3_buffer = io.BytesIO()
    v3.save(v3_buffer, format="PNG")
    v3_bytes = v3_buffer.getvalue()
    v3_buffer.close()
    jacket_buffer = io.BytesIO()
    jacket_pil_image.save(jacket_buffer, format="PNG")
    jacket_bytes = jacket_buffer.getvalue()
    jacket_buffer.close()
    return v1_bytes, v3_bytes, jacket_bytes
