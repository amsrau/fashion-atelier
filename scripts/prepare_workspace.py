import concurrent.futures
import json
import os
import shutil
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv()

DATA_DIR = ROOT / "data"
LOOKS_DIR = ROOT / "assets" / "looks"
FABRICS_DIR = ROOT / "assets" / "fabrics"
RENDERS_DIR = ROOT / "assets" / "renders"

for d in (DATA_DIR, LOOKS_DIR, FABRICS_DIR, RENDERS_DIR):
    d.mkdir(parents=True, exist_ok=True)

CATALOG_SRC = Path(os.environ.get("CATALOG_SRC", ROOT / "data" / "lookbook_catalog.json"))
INTEL_SRC = Path(os.environ.get("INTEL_SRC", ROOT / "data" / "fashion_intel.json"))
AUDIT_SRC = Path(os.environ.get("AUDIT_SRC", ROOT / "AUDIT_REPORT.md"))

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def effective_theme(r):
    v = r.get("vision") or {}
    tb = v.get("theme_bucket", "Other")
    tt = (r.get("thread_title") or "").lower()
    pk = v.get("post_kind", "")
    if pk != "single_outfit" and tb == "Footwear, Watch & Style Guides":
        return "Footwear, Watch & Style Guides"
    if any(k in tt for k in ["old money", "look rich", "luxury fabric", "classy man", "elegant outfit"]):
        if tb in ("Elevated Everyday & Knit-Denim", "Smart Casual & Blazer-Chino", "Old Money & Quiet Luxury"):
            return "Old Money & Quiet Luxury"
    if any(k in tt for k in ["date night", "couple dinner", "all-black", "all black"]):
        if "all-black" in tt or "all black" in tt:
            return "Monochrome & Dark Noir"
        if tb in ("Elevated Everyday & Knit-Denim", "Smart Casual & Blazer-Chino"):
            return "Date Night & Evening Sharp"
    if any(k in tt for k in ["office", "work outfits", "interview", "boss before you speak", "office suits"]):
        if tb in ("Smart Casual & Blazer-Chino", "Boardroom & Executive Tailoring"):
            return "Boardroom & Executive Tailoring"
    if tb == "Formal / Event":
        return "Boardroom & Executive Tailoring"
    return tb


def copy_assets_and_build_catalog():
    shutil.copy2(INTEL_SRC, DATA_DIR / "fashion_intel.json")
    if AUDIT_SRC.exists():
        shutil.copy2(AUDIT_SRC, ROOT / "AUDIT_REPORT.md")

    with open(CATALOG_SRC, "r", encoding="utf-8") as f:
        raw = json.load(f)

    by_dhash = {}
    for r in raw["records"]:
        dh = r.get("dhash")
        if dh and r.get("vision"):
            by_dhash.setdefault(dh, []).append(r)

    lookbook_items = []
    copied = 0
    for dh, grp in by_dhash.items():
        # Prefer channels that have clean dual-panel / original imagery first
        priority = {"_menstylish": 0, "gentelmenoutfit": 1, "Mensoutfitpxs": 2, "Elegantmanx": 3, "manly_talks": 4, "MensFits_": 5, "MensCanvas": 6}
        grp_sorted = sorted(grp, key=lambda x: priority.get(x["channel_handle"], 9))
        r = grp_sorted[0]
        src_img = Path(r.get("local_path") or "")
        if not src_img.exists():
            continue
        ext = src_img.suffix.lower() or ".jpg"
        dest_name = f"{dh}{ext}"
        dest_img = LOOKS_DIR / dest_name
        if not dest_img.exists():
            shutil.copy2(src_img, dest_img)
            copied += 1

        v = r["vision"]
        g = v.get("garments") or {}
        outer = g.get("outer_layer") or {}
        inner = g.get("inner_top") or {}
        bottom = g.get("bottom") or {}
        shoe = g.get("footwear") or {}

        lookbook_items.append({
            "dhash": dh,
            "img": f"assets/looks/{dest_name}",
            "post_kind": v.get("post_kind", ""),
            "theme": effective_theme(r),
            "channel": "@" + r["channel_handle"],
            "channels_all": sorted({"@" + x["channel_handle"] for x in grp}),
            "repeats": len(grp),
            "url": r["url"],
            "title": (r.get("thread_title") or "").replace("\n", " ").strip()[:80],
            "formula": v.get("silhouette_formula", ""),
            "color_label": v.get("color_combo_label", ""),
            "palette": [c for c in (v.get("palette_hex") or []) if isinstance(c, str) and c.startswith("#")],
            "outer": outer.get("item", "none"),
            "outer_hex": outer.get("hex", ""),
            "outer_fabric": outer.get("fabric", ""),
            "inner": inner.get("item", "none"),
            "inner_hex": inner.get("hex", ""),
            "bottom": bottom.get("item", "none"),
            "bottom_hex": bottom.get("hex", ""),
            "shoe": shoe.get("item", "none"),
            "shoe_hex": shoe.get("hex", ""),
            "summary": v.get("summary", ""),
        })

    lookbook_items.sort(key=lambda x: (-x["repeats"], x["theme"], x["channel"]))
    with open(DATA_DIR / "lookbook_catalog.json", "w", encoding="utf-8") as f:
        json.dump(lookbook_items, f, indent=2)
    print(f"Copied {copied} lookbook images; indexed {len(lookbook_items)} items -> {DATA_DIR / 'lookbook_catalog.json'}")


FABRIC_PROMPTS = {
    "wool": "Uniform edge-to-edge close-up textile surface of mid-grey (#888888) Italian worsted hopsack wool cloth, filling the entire frame evenly with fine woven yarns, flat lighting, zero borders, zero text.",
    "knit": "Macro studio photograph of neutral mid-grey (#888888) fine-gauge cashmere merino knitwear jersey stitch texture filling the entire square frame, soft knit loops, even diffused lighting, zero text.",
    "oxford": "Macro studio photograph of neutral mid-light grey (#949494) heavy Oxford cotton shirting basketweave texture filling the entire frame, even lighting, zero folds, zero text.",
    "denim": "Macro studio photograph of neutral mid-grey (#808080) washed denim 3x1 diagonal twill weave texture filling the entire square frame edge to edge, no selvedge border, even lighting.",
    "linen": "Macro studio photograph of neutral light-grey (#929292) washed Irish linen slub fabric weave texture filling the entire frame, organic flax yarns, even lighting, zero text.",
    "suede": "Uniform edge-to-edge macro texture of neutral mid-grey (#848484) velvety brushed calfskin suede fiber nap filling the entire frame under flat diffused lighting, zero seams, zero folds, zero text.",
    "leather": "Uniform edge-to-edge macro texture of neutral grey (#787878) full-grain calfskin pebble leather surface filling the entire square frame under soft diffused studio light, zero seams, zero text.",
}

THEME_SHOOTS = [
    ("smart_casual", "Midnight Navy (#1F2E46) hopsack wool unstructured blazer over a Crisp White (#F7F6F2) spread-collar dress shirt, Stone Khaki (#CFC3AE) slim chino trousers, Dark Cognac (#6B442A) suede penny loafers, matching cognac belt, white pocket square, silver watch"),
    ("elevated_everyday", "Sand Taupe (#A58A6C) brushed wool overshirt worn open over a Charcoal (#33363A) heavyweight crew tee, Mid-Indigo (#466789) straight selvedge jeans, Crisp White (#F4F3EF) minimal leather sneakers, dark brown belt, steel field watch"),
    ("old_money", "Warm Cream (#CBB99E) cashmere-wool blazer over an Ivory (#F4EFE4) ribbed knit polo, Espresso Brown (#4B3629) tailored pleated wool trousers, Dark Chocolate (#5C3A21) suede penny loafers, matching suede belt, gold dress watch"),
    ("boardroom", "Midnight Navy (#2C3545) double-breasted worsted wool suit jacket and matching navy tailored trousers over a Stark White (#FFFFFF) poplin dress shirt, Jet Black (#1C1C1E) cap-toe leather oxfords, crisp white folded pocket square, silver dress watch"),
    ("monochrome_noir", "Charcoal (#2D3035) structured blazer layered over a Jet Black (#151618) fine merino turtleneck sweater, Jet Black (#151618) tailored wool trousers, Jet Black (#141416) polished leather Chelsea boots, silver black-dial chronograph"),
    ("cold_weather", "Warm Camel (#B58D63) double-faced wool overcoat worn open over a Jet Black (#1A1B1E) fine rib turtleneck, Charcoal (#3C3F44) flannel tailored trousers, Dark Brown (#4D3122) calfskin Chelsea boots, gold dress watch"),
    ("resort_linen", "Dusty Rose (#C98C8E) relaxed open-collar washed linen long-sleeve shirt with sleeves neatly rolled once, Ecru Off-White (#F1ECE1) relaxed pleated Irish linen trousers, Sand Beige (#B99A73) unlined suede penny loafers, woven sand suede belt"),
    ("street_utility", "Matte Black (#22252A) nylon-twill bomber jacket layered over a Heather Grey (#B2B6BC) heavyweight cotton pullover hoodie, Washed Charcoal (#3C3F44) straight denim jeans, Minimal Crisp White (#F5F4F0) calfskin sneakers"),
    ("date_night", "Deep Burgundy (#5E1E2B) tailored single-breasted dinner jacket over a Jet Black (#151618) fine silk-knit polo shirt, Charcoal Black (#1E2024) pleated tailored trousers, Jet Black (#161618) sleek Chelsea dress boots, white pocket square, gold watch"),
]


def gen_image(prompt, out_path, aspect="1:1"):
    if out_path.exists():
        return f"cached:{out_path.name}"
    for model_name in ("gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect),
                ),
            )
            for cand in resp.candidates or []:
                if cand and getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                    for part in cand.content.parts:
                        if part.inline_data:
                            with open(out_path, "wb") as f:
                                f.write(part.inline_data.data)
                            return f"generated:{out_path.name}({model_name})"
        except Exception as exc:
            print(f"Warn {out_path.name} on {model_name}: {exc}")
    return f"empty:{out_path.name}"


def main():
    t0 = time.time()
    copy_assets_and_build_catalog()

    # Run fabric tiles + 9 theme shoots concurrently
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for fname, fp in FABRIC_PROMPTS.items():
            jobs.append(ex.submit(gen_image, fp, FABRICS_DIR / f"{fname}.png", "1:1"))
        for tid, desc in THEME_SHOOTS:
            prompt = (
                "High-resolution luxury menswear e-commerce editorial lookbook board on a warm cream-sand seamless studio backdrop (#DAC3A3). "
                "Center: invisible ghost-mannequin standing outfit cropped strictly from below the neck/collar down to the shoes (NO mannequin head, NO plastic face, NO neck cap, completely natural editorial torso crop with hands loosely tucked near trouser pockets). "
                f"Outfit: {desc}. "
                "Left vertical flat-lay column: the matching garments neatly folded stacked vertically. "
                "Right vertical column: slim acetate sunglasses, luxury watch, and coiled matching leather belt. "
                "Authentic macro fabric textures showing real woven cloth fibers, natural garment drape folds, crisp stitching seams, suede grain, and diffused editorial lighting. Completely clean image with zero text, zero brand labels, zero logos, zero watermarks."
            )
            jobs.append(ex.submit(gen_image, prompt, RENDERS_DIR / f"theme_{tid}.png", "3:4"))

        for fut in concurrent.futures.as_completed(jobs):
            print(" ->", fut.result())

    print(f"Workspace ready in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    main()
