import hashlib
import json
import mimetypes
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
load_dotenv()

RENDERS_DIR = ROOT / "assets" / "renders"
RENDERS_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("ATELIER_HOST", "127.0.0.1")
PORT = int(os.environ.get("ATELIER_PORT", "8765"))

_client = None


def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client


OUTER_LABELS = {
    "none": None,
    "blazer": "single-breasted unstructured blazer",
    "double_breasted": "double-breasted peak-lapel tailored blazer",
    "suit_jacket": "structured single-breasted tailored suit jacket",
    "overshirt": "structured buttoned overshirt with twin chest flap pockets",
    "bomber": "minimalist zipped Harrington bomber jacket",
    "suede_jacket": "clean collared minimalist jacket",
    "overcoat": "long mid-thigh single-breasted tailored overcoat",
}

INNER_LABELS = {
    "dress_shirt": "crisp long-sleeve spread-collar dress shirt with structured cuffs",
    "oxford_shirt": "long-sleeve button-down collar Oxford shirt with cuffs",
    "polo": "long-sleeve fine knit open-placket polo shirt with ribbed cuffs",
    "turtleneck": "long-sleeve fine ribbed mock/turtleneck knit sweater",
    "sweater": "long-sleeve clean crewneck knit sweater",
    "crew_tee": "short-sleeve heavyweight tailored crewneck t-shirt",
    "hoodie": "long-sleeve minimalist heavyweight pullover hoodie",
}

BOTTOM_LABELS = {
    "trousers": "pleated tailored dress trousers with sharp crease",
    "chinos": "slim-tailored cotton twill chino trousers",
    "jeans": "clean straight-leg selvedge denim jeans",
    "linen_trousers": "relaxed draped pleated summer trousers",
}

FOOTWEAR_LABELS = {
    "sneakers": "minimal low-top court sneakers",
    "loafers": "handsewn penny loafers",
    "oxfords": "sleek cap-toe dress oxford shoes",
    "chelsea": "slim almond-toe Chelsea dress boots",
}

FABRIC_LABELS = {
    "wool": "textured Italian worsted hopsack wool",
    "knit": "soft brushed fine-gauge merino cashmere knit",
    "oxford": "crisp woven heavy Oxford cotton",
    "denim": "authentic 3x1 selvedge twill weave denim",
    "linen": "natural slubbed Irish linen weave",
    "suede": "velvety napped brushed suede",
    "leather": "full-grain burnished calfskin leather",
}


def build_look_prompt(payload):
    outer = payload.get("outer", "none")
    inner = payload.get("inner", "dress_shirt")
    bottom = payload.get("bottom", "chinos")
    footwear = payload.get("footwear", "loafers")

    oc = payload.get("outerColor", "#1F2E46")
    ic = payload.get("innerColor", "#F7F6F2")
    bc = payload.get("bottomColor", "#CFC3AE")
    fc = payload.get("footwearColor", "#6B442A")
    blc = payload.get("beltColor", "#6B442A")

    of = FABRIC_LABELS.get(payload.get("outerFabric", "wool"), "worsted wool")
    inf = FABRIC_LABELS.get(payload.get("innerFabric", "oxford"), "cotton poplin")
    bf = FABRIC_LABELS.get(payload.get("bottomFabric", "oxford"), "cotton twill")
    ff = FABRIC_LABELS.get(payload.get("footwearFabric", "suede"), "calfskin")

    outer_desc = ""
    outer_flat = ""
    if outer != "none" and OUTER_LABELS.get(outer):
        o_txt = f"{payload.get('outerColorName', oc)} ({oc}) {of} {OUTER_LABELS[outer]}"
        outer_desc = f"an outer layer of {o_txt} worn open over "
        outer_flat = f"folded {o_txt}, "

    tuck_note = "neatly tucked in with a visible buckle leather belt" if payload.get("tucked") else "worn cleanly untucked"
    psq_note = " with a crisp white folded linen pocket square in the breast welt pocket" if (outer in ("blazer", "double_breasted", "suit_jacket") and payload.get("pocketSquare")) else ""
    metal_desc = "warm yellow-gold" if payload.get("watchMetal") == "gold" else "brushed stainless steel"

    inner_txt = f"{payload.get('innerColorName', ic)} ({ic}) {inf} {INNER_LABELS.get(inner, 'shirt')}"
    bottom_txt = f"{payload.get('bottomColorName', bc)} ({bc}) {bf} {BOTTOM_LABELS.get(bottom, 'trousers')}"
    shoe_txt = f"{payload.get('footwearColorName', fc)} ({fc}) {ff} {FOOTWEAR_LABELS.get(footwear, 'shoes')}"
    belt_txt = f"coiled {payload.get('beltColorName', blc)} ({blc}) leather belt with {metal_desc} buckle"

    sleeve_note = " Ensure the top garment shows complete natural hanging sleeves down both sides (NEVER sleeveless, NEVER a sleeveless vest, NO mannequin plastic arms)." if outer == "none" else ""

    return (
        "High-resolution luxury menswear e-commerce editorial lookbook board on a warm cream-sand seamless studio backdrop (#DAC3A3). "
        "Center column: invisible ghost-mannequin standing outfit cropped cleanly below the neck/collar down to the shoes (NO mannequin head, NO plastic face, NO neck plug, natural headless editorial studio crop). "
        f"The outfit wears {outer_desc}{inner_txt} ({tuck_note}){psq_note}, paired with {bottom_txt}, and {shoe_txt}.{sleeve_note} "
        f"Left vertical column: crisp flat-lay stack of {outer_flat}folded {inner_txt}, neatly folded {bottom_txt}, and pair of {shoe_txt}. "
        f"Right vertical column: slim tortoiseshell sunglasses, classic {metal_desc} dress timepiece, and {belt_txt}. "
        "Photorealistic macro textile fidelity showing real fabric yarns, wool nap, knit ribbing, twill weave, stitched seams, and natural gravity creases under soft studio lighting. Zero text, zero labels, zero logos, zero watermarks."
    )


class AtelierHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, code, data):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        req_path = unquote(parsed.path)

        if req_path == "/api/health":
            renders_count = len(list(RENDERS_DIR.glob("*.png")))
            looks_count = len(list((ROOT / "assets" / "looks").glob("*")))
            return self._send_json(200, {"ok": True, "looks": looks_count, "renders_cached": renders_count})

        if req_path in ("/", ""):
            req_path = "/index.html"

        target = (ROOT / req_path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            return self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        ctype, _ = mimetypes.guess_type(str(target))
        if not ctype:
            ctype = "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if req_path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/render-look":
            return self._send_json(HTTPStatus.NOT_FOUND, {"error": "Unknown endpoint"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:
            return self._send_json(400, {"error": f"Invalid JSON: {e}"})

        # Normalize signature key for disk cache
        sig_fields = [
            body.get("outer", "none"), body.get("inner", ""), body.get("bottom", ""), body.get("footwear", ""),
            body.get("outerColor", "").lower(), body.get("innerColor", "").lower(),
            body.get("bottomColor", "").lower(), body.get("footwearColor", "").lower(),
            body.get("beltColor", "").lower(),
            body.get("outerFabric", "wool"), body.get("innerFabric", "oxford"),
            body.get("bottomFabric", "oxford"), body.get("footwearFabric", "suede"),
            str(bool(body.get("tucked"))), str(bool(body.get("pocketSquare"))), body.get("watchMetal", "silver"),
        ]
        key = hashlib.sha1("|".join(sig_fields).encode("utf-8")).hexdigest()[:16]
        out_name = f"custom_{key}.png"
        out_path = RENDERS_DIR / out_name

        if out_path.exists():
            return self._send_json(200, {"status": "cached", "url": f"assets/renders/{out_name}", "elapsed_s": 0.0})

        if not os.environ.get("GEMINI_API_KEY"):
            return self._send_json(500, {"error": "GEMINI_API_KEY missing in environment"})

        t0 = time.time()
        prompt = build_look_prompt(body)
        try:
            img_bytes = None
            for model_name in ("gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"):
                resp = get_client().models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="3:4"),
                    ),
                )
                for cand in resp.candidates or []:
                    if cand and getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                        for part in cand.content.parts:
                            if part.inline_data:
                                img_bytes = part.inline_data.data
                                break
                    if img_bytes:
                        break
                if img_bytes:
                    break
            if not img_bytes:
                return self._send_json(502, {"error": "Model returned no image data"})
            out_path.write_bytes(img_bytes)
            return self._send_json(200, {
                "status": "generated",
                "url": f"assets/renders/{out_name}",
                "elapsed_s": round(time.time() - t0, 2),
            })
        except Exception as e:
            return self._send_json(500, {"error": str(e)})


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), AtelierHandler)
    print(f"Atelier 30 Fashion Workspace running at http://{HOST}:{PORT}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
