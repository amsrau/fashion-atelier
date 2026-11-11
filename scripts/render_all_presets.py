import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(ROOT / ".env")
load_dotenv()
from server import build_look_prompt
import build_studio_v2 as bsv2

COLOR_NAMES = {
    "#1f2e46": "midnight navy",
    "#1e2b42": "midnight navy",
    "#24344d": "deep navy",
    "#2c3545": "slate navy",
    "#383b40": "charcoal grey",
    "#3c3f44": "charcoal grey",
    "#43464b": "dark charcoal grey",
    "#2d3035": "charcoal black",
    "#24262a": "deep charcoal black",
    "#22252a": "matte charcoal black",
    "#151618": "jet black",
    "#161719": "jet black",
    "#17181b": "jet black",
    "#18191b": "jet black",
    "#191a1d": "jet black",
    "#161618": "jet black",
    "#141416": "jet black",
    "#1c1c1e": "jet black",
    "#1a1b1d": "jet black",
    "#1a1b1e": "jet black",
    "#1e2024": "charcoal black",
    "#f7f6f2": "crisp white",
    "#f8f7f3": "crisp white",
    "#ffffff": "crisp pure white",
    "#f5f4f0": "clean off-white",
    "#f4f3ef": "clean off-white",
    "#f4efe4": "warm ivory cream",
    "#f3efe4": "warm ivory cream",
    "#f1ece1": "ecru cream",
    "#ece5d4": "warm ivory cream",
    "#eae5d8": "ecru off-white",
    "#eae3d3": "ecru off-white",
    "#cbb99e": "beige cream",
    "#cfc3ae": "warm stone khaki",
    "#c9ba9e": "warm sand khaki",
    "#d5c9b4": "warm stone beige",
    "#a58a6c": "warm tan camel",
    "#b58c5e": "warm camel tan",
    "#b58d63": "warm camel tan",
    "#b99a73": "sand tan",
    "#8fb3d6": "sky blue",
    "#8eb4d7": "sky blue",
    "#436180": "dusty slate blue",
    "#3a5673": "medium indigo denim blue",
    "#3e5c7a": "medium indigo denim blue",
    "#3d5b7e": "medium indigo denim blue",
    "#466789": "classic indigo denim blue",
    "#8f9397": "heather mid grey",
    "#b2b6bc": "heather light grey",
    "#4e5c3e": "olive green",
    "#4b593b": "olive green",
    "#424f34": "dark olive drab",
    "#5e1e2b": "rich burgundy",
    "#4e3222": "rich chocolate espresso brown",
    "#4b3629": "dark espresso brown",
    "#4d3122": "dark brown",
    "#4d3222": "dark brown",
    "#4a2e20": "dark espresso brown",
    "#6b442a": "tobacco brown",
    "#5c3a21": "espresso brown",
    "#5c3b28": "espresso brown",
    "#8b4e24": "warm cognac tan",
    "#c98c8e": "dusty rose",
    "#222224": "black",
}

def cname(hx):
    return COLOR_NAMES.get((hx or "").lower(), hx)

def render_one(task):
    fid, fm = task
    out_path = ROOT / fm["shootImg"]
    if out_path.exists() and out_path.stat().st_size > 10000:
        return (fid, "cached", 0.0)

    payload = {
        "outer": fm["outer"],
        "inner": fm["inner"],
        "bottom": fm["bottom"],
        "footwear": fm["footwear"],
        "outerFabric": fm["outerFabric"],
        "innerFabric": fm["innerFabric"],
        "bottomFabric": fm["bottomFabric"],
        "footwearFabric": fm["footwearFabric"],
        "outerColor": fm["outerColor"],
        "outerColorName": cname(fm["outerColor"]),
        "innerColor": fm["innerColor"],
        "innerColorName": cname(fm["innerColor"]),
        "bottomColor": fm["bottomColor"],
        "bottomColorName": cname(fm["bottomColor"]),
        "footwearColor": fm["footwearColor"],
        "footwearColorName": cname(fm["footwearColor"]),
        "beltColor": fm["beltColor"],
        "beltColorName": cname(fm["beltColor"]),
        "tucked": fm["tucked"],
        "pocketSquare": fm["pocketSquare"],
        "watchMetal": fm["watchMetal"],
    }
    prompt = build_look_prompt(payload)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    t0 = time.time()
    last_err = None
    for model_name in ("gemini-2.5-flash-image", "gemini-3.1-flash-image-preview"):
        try:
            resp = client.models.generate_content(
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
                            out_path.write_bytes(part.inline_data.data)
                            return (fid, model_name, round(time.time() - t0, 2))
        except Exception as e:
            last_err = str(e)
    return (fid, f"ERROR: {last_err}", round(time.time() - t0, 2))


def main():
    tasks = []
    for theme in bsv2.themes_catalog:
        for fm in theme["formulas"]:
            tasks.append((fm["id"], fm))

    print(f"Checking/rendering {len(tasks)} total curated formula shoots...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(render_one, t): t[0] for t in tasks}
        for fut in as_completed(futs):
            fid, status, sec = fut.result()
            print(f"[{fid}] {status} ({sec}s)")


if __name__ == "__main__":
    main()
