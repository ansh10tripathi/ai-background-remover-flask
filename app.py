import os
import uuid
import time
import logging
import imghdr
from pathlib import Path

from collections import defaultdict
from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", uuid.uuid4().hex)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", 10)) * 1024 * 1024

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func        = get_remote_address,
    app             = app,
    default_limits  = [],                  # no global limit — applied per route
    storage_uri     = "memory://",
)

# Per-IP daily quota — 50 requests per calendar day stored in memory
_daily_counts: dict = defaultdict(lambda: {"date": "", "count": 0})
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 50))

def check_daily_quota() -> bool:
    """Returns True if the IP is within quota, False if exceeded."""
    ip      = get_remote_address()
    today   = time.strftime("%Y-%m-%d")
    record  = _daily_counts[ip]
    if record["date"] != today:            # new day — reset counter
        record["date"]  = today
        record["count"] = 0
    record["count"] += 1
    return record["count"] <= DAILY_LIMIT

UPLOAD_FOLDER      = Path("static/uploads")
OUTPUT_FOLDER      = Path("static/outputs")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {"jpeg", "png", "webp", "gif"}
MAX_IMAGE_DIM      = 2048
FILE_MAX_AGE_SECS  = 3600

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

log.info("Loading rembg u2net session...")
REMBG_SESSION = new_session("u2net")
log.info("rembg session ready.")

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_extension(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_magic_bytes(path):
    return imghdr.what(path) in ALLOWED_MIME_TYPES

def unique_path(folder, suffix):
    return folder / f"{uuid.uuid4().hex}{suffix}"

def safe_image_open(path):
    """Open, verify, resize if needed, always return RGBA copy."""
    with Image.open(path) as img:
        img.verify()
    with Image.open(path) as img:
        img = img.convert("RGBA")
        if max(img.size) > MAX_IMAGE_DIM:
            img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM), Image.LANCZOS)
        return img.copy()

def cleanup_old_files(folder):
    now = time.time()
    for f in folder.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            if now - f.stat().st_mtime > FILE_MAX_AGE_SECS:
                f.unlink(missing_ok=True)

# ── Image processing functions ────────────────────────────────────────────────

def run_remove(input_img):
    """Remove background — returns RGBA with transparent bg."""
    return remove(input_img, session=REMBG_SESSION)

def run_blur(input_img, rembg_img):
    """Blur background, keep subject sharp — returns RGBA."""
    alpha      = rembg_img.split()[3]
    blurred    = input_img.convert("RGB").filter(ImageFilter.GaussianBlur(radius=15))
    blurred    = blurred.convert("RGBA")
    blurred.paste(rembg_img, (0, 0), mask=alpha)
    return blurred

def _enhance(rgb):
    rgb = ImageEnhance.Brightness(rgb).enhance(1.15)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.20)
    rgb = ImageEnhance.Color(rgb).enhance(1.25)
    rgb = ImageEnhance.Sharpness(rgb).enhance(2.00)
    return rgb

def run_enhance_with_bg(input_img):
    """Enhance full image including background — returns RGB."""
    return _enhance(input_img.convert("RGB"))

# ✅ FIX: accepts cached rembg_img directly instead of re-running rembg
def run_enhance_no_bg(rembg_img):
    """Enhance subject only using cached rembg output — returns RGBA."""
    r, g, b, alpha = rembg_img.split()
    rgb            = _enhance(Image.merge("RGB", (r, g, b)))
    result         = rgb.convert("RGBA")
    result.putalpha(alpha)
    return result

# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(413)
def too_large(e):
    return render_template("index.html", error="File too large. Maximum size is 10MB."), 413

@app.errorhandler(429)
def rate_limited(e):
    log.warning("Rate limit hit — IP: %s", get_remote_address())
    return render_template("429.html", reason="minute", daily_limit=DAILY_LIMIT), 429

@app.errorhandler(500)
def server_error(e):
    log.exception("Unhandled server error")
    return render_template("index.html", error="Something went wrong. Please try again."), 500

# ── Main route ────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])   # 10 POSTs per minute per IP
def index():

    if request.method == "GET":
        return render_template("index.html")

    # Check daily quota before doing any work
    if not check_daily_quota():
        log.warning("Daily quota exceeded — IP: %s", get_remote_address())
        return render_template("429.html", reason="daily", daily_limit=DAILY_LIMIT), 429

    cleanup_old_files(UPLOAD_FOLDER)
    cleanup_old_files(OUTPUT_FOLDER)

    file           = request.files.get("image")
    action         = request.form.get("action", "remove")
    enhance_mode   = request.form.get("enhance_mode", "no_bg")
    saved_filename = request.form.get("saved_filename", "").strip()
    saved_rembg    = request.form.get("saved_rembg", "").strip()

    # ── Load images ───────────────────────────────────────────────────────────
    try:
        if file and file.filename:
            if not allowed_extension(file.filename):
                return render_template("index.html", error="Invalid file type. Please upload JPG, PNG or WEBP.")
            filename   = secure_filename(file.filename)
            input_path = UPLOAD_FOLDER / filename
            file.save(str(input_path))
            if not allowed_magic_bytes(str(input_path)):
                input_path.unlink(missing_ok=True)
                return render_template("index.html", error="File content is not a valid image.")
            input_img      = safe_image_open(str(input_path))
            saved_filename = filename
            # Run rembg once and cache — blur and enhance_no_bg both reuse this
            rembg_img      = remove(input_img, session=REMBG_SESSION)
            rembg_path     = unique_path(OUTPUT_FOLDER, "_rembg.png")
            rembg_img.save(str(rembg_path))
            saved_rembg    = rembg_path.name
            log.info("Uploaded and rembg processed: %s", filename)

        elif saved_filename and saved_rembg:
            input_path = UPLOAD_FOLDER / secure_filename(saved_filename)
            rembg_path = OUTPUT_FOLDER / secure_filename(saved_rembg)
            if not input_path.exists() or not rembg_path.exists():
                return render_template("index.html", error="Session expired. Please upload again.")
            input_img = safe_image_open(str(input_path))
            rembg_img = safe_image_open(str(rembg_path))
            log.info("Reusing: %s", saved_filename)

        else:
            return render_template("index.html", error="Please upload an image first.")

    except Exception:
        log.exception("Error loading image")
        return render_template("index.html", error="Could not load image. Please try again.")

    # ── Apply action ──────────────────────────────────────────────────────────
    try:
        if action == "remove":
            result_path = unique_path(OUTPUT_FOLDER, "_removed.png")
            rembg_img.save(str(result_path))
            result_label = "Background Removed"
            badge        = "badge-violet"

        elif action == "blur":
            result      = run_blur(input_img, rembg_img)
            result_path = unique_path(OUTPUT_FOLDER, "_blurred.png")
            result.save(str(result_path))
            result_label = "Background Blurred"
            badge        = "badge-sky"

        elif action == "enhance":
            if enhance_mode == "with_bg":
                result      = run_enhance_with_bg(input_img)
                result_path = unique_path(OUTPUT_FOLDER, "_enhanced_withbg.jpg")
                result.save(str(result_path), format="JPEG", quality=95)
                result_label = "Enhanced (With BG)"
            else:
                # ✅ FIX: pass cached rembg_img, not input_img
                result      = run_enhance_no_bg(rembg_img)
                result_path = unique_path(OUTPUT_FOLDER, "_enhanced_nobg.png")
                result.save(str(result_path), format="PNG")
                result_label = "Enhanced (No BG)"
            badge = "badge-emerald"

        else:
            return render_template("index.html", error="Unknown action.")

    except Exception:
        log.exception("Error applying action: %s", action)
        return render_template("index.html", error="Processing failed. Please try again.")

    return render_template(
        "index.html",
        original_image = str(input_path),
        result_image   = str(result_path),
        result_label   = result_label,
        badge          = badge,
        saved_filename = saved_filename,
        saved_rembg    = saved_rembg,
        action         = action,
        enhance_mode   = enhance_mode,
    )

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=debug_mode
    )