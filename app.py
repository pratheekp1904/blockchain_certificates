import os
import json
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory
from dotenv import load_dotenv
from web3 import Web3

# PDF generation (ReportLab)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

load_dotenv()

RPC = os.getenv("RPC_URL", "http://127.0.0.1:8545")
PRIVATE_KEY = os.getenv("DEPLOYER_PRIVATE_KEY")  # optional
w3 = Web3(Web3.HTTPProvider(RPC))
assert w3.is_connected(), "Cannot connect to RPC node"

# Load contract ABI and address
with open("contract_abi.json") as f:
    data = json.load(f)
ABI = data["abi"]
CONTRACT_ADDRESS = data["address"]

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# Deployer address
if PRIVATE_KEY:
    deployer_addr = w3.eth.account.from_key(PRIVATE_KEY).address
else:
    deployer_addr = w3.eth.accounts[0]  # unlocked account from Ganache

app = Flask(__name__)

# Paths for generated PDFs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CERT_DIR = os.path.join(STATIC_DIR, "certificates")
os.makedirs(CERT_DIR, exist_ok=True)


def send_transaction(contract_function, *args):
    """Helper to send tx using PK or unlocked account"""
    if PRIVATE_KEY:
        tx = contract_function(*args).build_transaction({
            "from": deployer_addr,
            "nonce": w3.eth.get_transaction_count(deployer_addr),
            "gas": 400000,
            "gasPrice": w3.to_wei("20", "gwei"),
            "chainId": w3.eth.chain_id
        })
        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt
    else:
        tx_hash = contract_function(*args).transact({"from": deployer_addr})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt


def generate_cert_id(institution: str, course: str) -> str:
    """
    Generate a 16-character random alphanumeric certificate ID.
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=16))


def certificate_pdf_filename(cert_id: str) -> str:
    return f"certificate_{cert_id}.pdf"


def certificate_pdf_path(cert_id: str) -> str:
    return os.path.join(CERT_DIR, certificate_pdf_filename(cert_id))


def ensure_certificate_pdf(student: str, course: str, institution: str, cert_id: str, issue_ts: int | None = None):
    """Create the certificate PDF if it doesn't already exist."""
    filepath = certificate_pdf_path(cert_id)
    if os.path.exists(filepath):
        return filepath

    # Landscape page
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Background color (light calm blue)
    c.setFillColorRGB(0.9, 0.95, 1)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Border
    margin = 1.5 * cm
    c.setLineWidth(4)
    c.setStrokeColor(colors.darkblue)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # Title
    c.setFont("Helvetica-Bold", 40)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 4 * cm, "Certificate of Completion")

    # Subtitle
    c.setFont("Helvetica-Oblique", 18)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 5.3 * cm, "Blockchain Certificates — Secure. Transparent. Immutable.")

    # Presented to
    c.setFont("Helvetica", 20)
    c.setFillColor(colors.darkgray)
    c.drawCentredString(width / 2, height - 8 * cm, "This is proudly presented to")
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.cornflowerblue)
    c.drawCentredString(width / 2, height - 10 * cm, student)

    # Course
    c.setFont("Helvetica", 20)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 12 * cm, f"For successfully completing the course:")
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 13.5 * cm, course)

    # Institution
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.green)
    c.drawCentredString(width / 2, height - 18 * cm, f"Issued by: {institution}")

    # Certificate ID and Issue Date
    pretty_date = datetime.fromtimestamp(issue_ts).strftime("%Y-%m-%d %H:%M:%S") if issue_ts else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, 5.5 * cm, f"Certificate ID: {cert_id}")
    c.drawCentredString(width / 2, 5 * cm, f"Issue Date: {pretty_date}")

    # Footer
    c.setFont("Helvetica-Oblique", 12)
    c.setFillColor(colors.gray)
    c.drawCentredString(width / 2, 2.5 * cm, "This certificate is recorded on an Ethereum-compatible blockchain.")

    c.showPage()
    c.save()
    return filepath


# ----------------- Web Routes -----------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/issue", methods=["GET", "POST"])
def issue_page():
    if request.method == "GET":
        return render_template("issue.html")

    student_name = request.form.get("studentName")
    course = request.form.get("course")
    institution = request.form.get("institution")

    if not student_name or not course or not institution:
        message = "❌ All fields are required!"
        return render_template("issue.html", message=message)

    certID = generate_cert_id(institution, course)
    certHash = certID

    try:
        receipt = send_transaction(
            contract.functions.issueCertificate,
            certID,
            student_name,
            course,
            institution,
            certHash
        )
        valid, _student, _course, _inst, issueDate = contract.functions.verifyCertificate(certID, certHash).call()

        ensure_certificate_pdf(student_name, course, institution, certID, issue_ts=issueDate if valid else None)
        pdf_url = url_for("download_certificate", cert_id=certID)

        message = f"🎓 Certificate issued successfully!"
        return render_template("issue.html", message=message, certID=certID, pdf_url=pdf_url)
    except Exception as e:
        return render_template("issue.html", message=f"❌ Error: {str(e)}")


@app.route("/verify", methods=["GET", "POST"])
def verify_page():
    if request.method == "GET":
        return render_template("verify.html")

    certID = request.form.get("certID")
    if not certID:
        return render_template("verify.html", message="❌ Please provide a Certificate ID")

    certHash = certID

    try:
        valid, student, course, inst, issueDate = contract.functions.verifyCertificate(certID, certHash).call()
        if not student:
            message = f"❌ Certificate {certID} not found"
            return render_template("verify.html", message=message)

        ensure_certificate_pdf(student, course, inst, certID, issue_ts=issueDate)
        pdf_url = url_for("download_certificate", cert_id=certID)

        cert = {
            "valid": valid,
            "student": student,
            "course": course,
            "institution": inst,
            "issueDate": issueDate
        }
        message = f"✅ Certificate {certID} verification complete"
        return render_template("verify.html", message=message, cert=cert, certID=certID, pdf_url=pdf_url)
    except Exception as e:
        return render_template("verify.html", message=f"❌ Error: {str(e)}")


# ----------------- API Routes -----------------
@app.route("/api/issue", methods=["POST"])
def api_issue():
    data = request.json
    required = ["studentName", "course", "institution"]
    if not all(k in data for k in required):
        return jsonify({"error": "missing fields"}), 400

    certID = generate_cert_id(data["institution"], data["course"])
    certHash = certID

    receipt = send_transaction(
        contract.functions.issueCertificate,
        certID,
        data["studentName"],
        data["course"],
        data["institution"],
        certHash
    )

    valid, _, _, _, issueDate = contract.functions.verifyCertificate(certID, certHash).call()
    ensure_certificate_pdf(data["studentName"], data["course"], data["institution"], certID, issue_ts=issueDate if valid else None)
    pdf_url = url_for("download_certificate", cert_id=certID)

    return jsonify({
        "status": "issued",
        "certID": certID,
        "tx_hash": receipt.transactionHash.hex(),
        "block": receipt.blockNumber,
        "pdf_url": pdf_url
    })


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.json
    certID = data.get("certID")
    if not certID:
        return jsonify({"error": "provide certID"}), 400

    certHash = certID
    valid, student, course, inst, issueDate = contract.functions.verifyCertificate(certID, certHash).call()

    pdf_created = None
    if student:
        ensure_certificate_pdf(student, course, inst, certID, issue_ts=issueDate)
        pdf_created = url_for("download_certificate", cert_id=certID)

    return jsonify({
        "valid": valid,
        "student": student,
        "course": course,
        "institution": inst,
        "issueDate": issueDate,
        "pdf_url": pdf_created
    })


# ----------------- Contract info -----------------
@app.route("/api/contract_info", methods=["GET"])
def contract_info():
    return jsonify({"address": CONTRACT_ADDRESS, "chainId": w3.eth.chain_id})


# ----------------- PDF Download -----------------
@app.route("/download/<cert_id>", methods=["GET"])
def download_certificate(cert_id):
    filename = certificate_pdf_filename(cert_id)
    fullpath = certificate_pdf_path(cert_id)
    if not os.path.exists(fullpath):
        return "Certificate PDF not found. Try verifying again to regenerate.", 404
    return send_from_directory(CERT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
