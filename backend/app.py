from flask import Flask, render_template, request
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from pathlib import Path
import mimetypes
import shutil

from datetime import datetime

from flask import redirect, url_for

from ai_generator import (
    generate_complaint,
    translate_to_english,
    generate_subject,
    english_to_telugu,
    translate_subject,
    clean_speech
)

from speech import speech_to_text

from flask import send_file
from flask import send_from_directory

from pdf_generator import (
    generate_telugu_pdf,
    generate_english_pdf
)

from database import (
    init_db,
    save_complaint,
    get_complaints,
    get_complaint_by_id,
    update_audio_path,
    get_statistics
)

from security_config import (
    init_security_headers,
    init_cors,
    limiter,
    validate_phone_number,
    validate_name,
    sanitize_filename,
    validate_audio_file
)

# Set template and static folders
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Security configuration
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['UPLOAD_FOLDER'] = '/app/audio'

# Initialize security features
init_security_headers(app)
init_cors(app)
limiter.init_app(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('/app/case_records', exist_ok=True)
os.makedirs('/app/generated', exist_ok=True)

init_db()

# Base URL for PDF generation (set via environment in production)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")


def load_station():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'station_config.json')
    if not os.path.exists(config_path):
        return {
            "station_name": "Police Station",
            "place": "Place",
            "district": "District",
            "station_name_telugu": "పోలీస్ స్టేషన్",
            "place_telugu": "ప్రదేశం",
            "district_telugu": "జిల్లా"
        }

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def dashboard():
    complaints = get_complaints()
    total_cases, today_cases, month_cases = get_statistics()

    return render_template(
        "dashboard.html",
        complaints=complaints,
        total_cases=total_cases,
        today_cases=today_cases,
        month_cases=month_cases
    )


@app.route("/record")
def record():
    return render_template("record.html")


@app.route("/settings")
def settings():
    station = load_station()
    return render_template("settings.html", station=station)


@app.route("/save_settings", methods=["POST"])
@limiter.limit("10 per minute")
def save_settings():
    station_name = request.form.get("station_name", "").strip()
    place = request.form.get("place", "").strip()
    district = request.form.get("district", "").strip()

    # Input validation
    if not station_name or not place or not district:
        return render_template("error.html", message="All fields are required."), 400

    if not validate_name(station_name) or not validate_name(place) or not validate_name(district):
        return render_template("error.html", message="Invalid characters in input. Only letters, spaces, dots, and hyphens allowed."), 400

    # Translate to Telugu (optional — settings still save if translation fails)
    try:
        station_name_telugu = english_to_telugu(station_name)
    except Exception:
        station_name_telugu = ""
    try:
        place_telugu = english_to_telugu(place)
    except Exception:
        place_telugu = ""
    try:
        district_telugu = english_to_telugu(district)
    except Exception:
        district_telugu = ""

    data = {
        "station_name": station_name,
        "place": place,
        "district": district,
        "station_name_telugu": station_name_telugu,
        "place_telugu": place_telugu,
        "district_telugu": district_telugu
    }

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'station_config.json')
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return redirect(url_for("dashboard"))


@app.route("/process", methods=["POST"])
@limiter.limit("20 per minute")
def process():
    complainant_name = request.form.get("complainant_name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()

    # Input validation
    if not complainant_name or not phone_number:
        return render_template("error.html", message="Name and phone number are required."), 400

    if not validate_name(complainant_name):
        return render_template("error.html", message="Invalid name. Only letters, spaces, dots, and hyphens allowed."), 400

    if not validate_phone_number(phone_number):
        return render_template("error.html", message="Invalid phone number. Must be a valid 10-digit Indian mobile number."), 400

    complainant_name_telugu = english_to_telugu(complainant_name)

    # Handle audio file (uploaded or recorded)
    if "audio" not in request.files and "recorded_audio" not in request.files:
        return render_template("error.html", message="No audio file provided."), 400

    if "audio" in request.files and request.files["audio"].filename != "":
        audio = request.files["audio"]
    else:
        audio = request.files["recorded_audio"]

    filename = sanitize_filename(audio.filename or "recorded.webm")
    if filename == "":
        filename = "recorded.webm"

    if not validate_audio_file(filename):
        return render_template("error.html", message="Invalid audio file format. Allowed: wav, mp3, m4a, ogg, webm, aac, flac"), 400

    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio.save(path)

    registered_on = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    try:
        text = speech_to_text(path)
        print(f"Speech to text result: {text}")
        cleaned_text = clean_speech(text)
        print(f"Cleaned text: {cleaned_text}")
        complaint = generate_complaint(cleaned_text, complainant_name_telugu)
        print(f"Complaint generated: {complaint[:100]}...")
        english = translate_to_english(complaint, complainant_name)
        print(f"English translation: {english[:100]}...")
        subject = generate_subject(complaint)
        print(f"Subject: {subject}")

        complaint_id = save_complaint(
            registered_on,
            complainant_name,
            complainant_name_telugu,
            phone_number,
            subject,
            filename,
            complaint,
            english
        )

        # Create Case Record Folder
        today = datetime.now()
        year = today.strftime("%Y")
        month = today.strftime("%B")
        date = today.strftime("%d-%m-%Y")

        case_folder_name = (
            f"C{complaint_id:03d}_"
            f"{complainant_name.replace(' ', '_')}_"
            f"{date}"
        )

        case_folder = Path("case_records", year, month, case_folder_name)
        case_folder.mkdir(parents=True, exist_ok=True)

        extension = os.path.splitext(filename)[1]
        audio_name = f"Complaint_Audio{extension}"
        audio_destination = case_folder / audio_name

        shutil.copy2(path, str(audio_destination))

        update_audio_path(complaint_id, str(audio_destination).replace("\\", "/"))

        # Load station configuration before rendering templates
        station = load_station()

        # Render HTML templates directly to avoid HTTP round-trip issues with gunicorn
        telugu_html = render_template(
            "result.html",
            complaint_id=complaint_id,
            speech=text,
            complaint=complaint,
            subject=subject,
            complainant_name=complainant_name_telugu,
            phone_number=phone_number,
            station_name=station["station_name"],
            place=station["place"],
            district=station["district"],
            station_name_telugu=station["station_name_telugu"],
            place_telugu=station["place_telugu"],
            district_telugu=station["district_telugu"],
            current_date=datetime.now().strftime("%d-%m-%Y"),
            case_name=case_folder_name
        )

        english_html = render_template(
            "english.html",
            english=english,
            subject=translate_subject(complaint),
            complainant_name=complainant_name,
            phone_number=phone_number,
            current_date=datetime.now().strftime("%d-%m-%Y"),
            station_name=station["station_name"],
            place=station["place"],
            district=station["district"],
            case_name=case_folder_name
        )

        # Generate PDFs from rendered HTML (non-blocking, background thread)
        import threading

        def generate_pdfs_in_thread():
            try:
                telugu_pdf = case_folder / "Complaint_Telugu.pdf"
                generate_telugu_pdf(str(telugu_pdf), complaint_id, telugu_html)
            except Exception as e:
                print(f"PDF generation failed (non-critical): {e}")
            try:
                english_pdf = case_folder / "Complaint_English.pdf"
                generate_english_pdf(str(english_pdf), complaint_id, english_html)
            except Exception as e:
                print(f"PDF generation failed (non-critical): {e}")

        thread = threading.Thread(target=generate_pdfs_in_thread)
        thread.start()

        station = load_station()

        return render_template(
            "result.html",
            complaint_id=complaint_id,
            speech=text,
            complaint=complaint,
            subject=subject,
            complainant_name=complainant_name_telugu,
            phone_number=phone_number,
            station_name=station["station_name"],
            place=station["place"],
            district=station["district"],
            station_name_telugu=station["station_name_telugu"],
            place_telugu=station["place_telugu"],
            district_telugu=station["district_telugu"],
            current_date=datetime.now().strftime("%d-%m-%Y"),
            case_name=case_folder_name
        )
    except Exception as e:
        import traceback
        print(f"Processing error: {e}")
        traceback.print_exc()
        return render_template(
            "error.html",
            message=f"Processing error: {str(e)}"
        )


@app.route("/english")
def english_page():
    return render_template("english.html", english="")

@app.route("/view_telugu/<int:complaint_id>")
def view_telugu(complaint_id):
    complaint = get_complaint_by_id(complaint_id)

    if not complaint:
        return "Complaint not found", 404

    station = load_station()

    # Create Case Name
    date = datetime.strptime(complaint[1], "%d-%m-%Y %I:%M %p").strftime("%d-%m-%Y")
    case_name = (
        f"C{complaint[0]:03d}_"
        f"{complaint[2].replace(' ', '_')}_"
        f"{date}"
    )

    return render_template(
        "result.html",
        complaint=complaint[7],
        subject=complaint[5],
        complainant_name=complaint[3],
        phone_number=complaint[4],
        station_name=station["station_name"],
        place=station["place"],
        district=station["district"],
        station_name_telugu=station["station_name_telugu"],
        place_telugu=station["place_telugu"],
        district_telugu=station["district_telugu"],
        current_date=datetime.now().strftime("%d-%m-%Y"),
        complaint_id=complaint_id,
        case_name=case_name
    )


@app.route("/view_english/<int:complaint_id>")
def view_english(complaint_id):
    complaint = get_complaint_by_id(complaint_id)

    if not complaint:
        return "Complaint not found", 404

    station = load_station()

    # Create Case Name
    date = datetime.strptime(complaint[1], "%d-%m-%Y %I:%M %p").strftime("%d-%m-%Y")
    case_name = (
        f"C{complaint[0]:03d}_"
        f"{complaint[2].replace(' ', '_')}_"
        f"{date}"
    )

    return render_template(
        "english.html",
        english=complaint[8],
        subject=translate_subject(complaint[5]),
        complainant_name=complaint[2],
        phone_number=complaint[4],
        current_date=datetime.now().strftime("%d-%m-%Y"),
        station_name=station["station_name"],
        place=station["place"],
        district=station["district"],
        case_name=case_name
    )


from pathlib import Path
from flask import send_file

@app.route("/case_audio/<path:filepath>")
def serve_case_audio(filepath):
    # Prevent path traversal
    filepath = Path(filepath)
    # Resolve to absolute path and ensure it's within case_records
    try:
        resolved_path = filepath.resolve()
        case_records_root = Path("case_records").resolve()
        # Check if the resolved path is within case_records directory
        if not str(resolved_path).startswith(str(case_records_root)):
            return "Audio file not found", 404
    except Exception:
        return "Audio file not found", 404

    if not resolved_path.exists():
        return "Audio file not found", 404

    # Guess MIME type based on file extension; ensure audio files serve as audio
    mime_type, _ = mimetypes.guess_type(str(resolved_path))
    if mime_type is None or not mime_type.startswith('audio/'):
        ext = resolved_path.suffix.lower()
        if ext == '.webm':
            mime_type = 'audio/webm'
        elif ext == '.wav':
            mime_type = 'audio/wav'
        elif ext == '.mp3':
            mime_type = 'audio/mpeg'
        elif ext == '.m4a':
            mime_type = 'audio/mp4'
        elif ext == '.ogg':
            mime_type = 'audio/ogg'
        elif ext == '.aac':
            mime_type = 'audio/aac'
        elif ext == '.flac':
            mime_type = 'audio/flac'
        else:
            mime_type = 'application/octet-stream'

    return send_file(resolved_path, mimetype=mime_type, as_attachment=False)


@app.route("/health")
def health():
    return {"status": "healthy"}, 200


@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", message="Internal server error. Please try again."), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)