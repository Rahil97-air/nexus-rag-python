"""Create a fictional, non-sensitive PDF for the first lesson."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "samples" / "handbook.pdf"
target.parent.mkdir(exist_ok=True)
canvas = Canvas(str(target), pagesize=A4)
sections = [
    ("Expense claims", [
        "Harbor Analytics - FICTIONAL TRAINING HANDBOOK",
        "Employees must submit expense claims within 30 calendar days",
        "of the purchase date. Attach an itemised receipt to each claim.",
        "Claims over INR 5,000 require approval from the department manager.",
        "Approved claims are paid in the next monthly payroll cycle.",
    ]),
    ("Remote work", [
        "Employees may work remotely for up to two days per week.",
        "They must obtain written approval from their team lead first.",
        "Core collaboration hours are 10:00 AM to 3:00 PM local time.",
        "Company laptops must use the approved VPN outside the office.",
    ]),
    ("Learning budget", [
        "Each employee has an annual learning budget of INR 12,000.",
        "The budget covers approved courses, books and certification exams.",
        "A manager must approve the learning request before purchase.",
        "Unused learning budget does not carry forward to the next year.",
    ]),
]
for number, (heading, lines) in enumerate(sections, 1):
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(50, 780, heading)
    canvas.setFont("Helvetica", 12)
    for index, line in enumerate(lines):
        canvas.drawString(50, 740 - index * 23, line)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(50, 40, f"Fictional example only | Page {number}")
    canvas.showPage()
canvas.save()
print(target)
