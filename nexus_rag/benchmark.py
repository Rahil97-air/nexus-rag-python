"""Fictional PDF fixture, built in memory. No user or employer data."""
from io import BytesIO
from textwrap import wrap
from reportlab.pdfgen.canvas import Canvas

SECTIONS = [
    ("Routine expense reimbursement", [
        "Routine expense claims must be submitted within 30 calendar days of purchase. An itemised receipt must accompany every claim. The employee should explain the business purpose and include the relevant cost centre. A bank statement alone is not a substitute for a receipt. This routine reimbursement deadline is different from the business travel booking deadline and the equipment incident reporting deadline.",
        "Routine claims over INR 5,000 require approval from the department manager. Finance checks receipts and cost codes after that approval. Approved routine claims are paid in the next monthly payroll cycle. A returned claim is not approved: the employee must correct the missing information. The department manager cannot approve their own reimbursement claim; their manager must review it instead.",
    ]),
    ("Hybrid working arrangements", [
        "Employees may work remotely for up to two days each week. They must obtain written approval from their team lead before working remotely. This rule concerns where normal work is performed; it is not a holiday or leave entitlement. The employee records the agreed days in the team calendar so colleagues can plan meetings and office coverage. A learning purchase requires a different approval process.",
        "Core collaboration hours are 10:00 AM to 3:00 PM local time. Remote staff should be reachable during this period unless an absence is agreed with their lead. Company laptops must use the approved VPN outside the office. Working remotely does not authorise copying customer files onto a personal computer. Questions about connection problems should go to the service desk, not the travel booking team.",
    ]),
    ("Professional learning allowance", [
        "Each employee has an annual learning budget of INR 12,000. It covers approved courses, books and certification exams. A manager must approve the learning request before purchase. The request should identify the skill being developed and explain how it supports the employee's role. This learning allowance is separate from business travel expenses and from the team's equipment procurement budget.",
        "Unused learning budget does not carry forward to the next year. Employees should record completed courses in their development plan. Buying several courses does not increase the annual limit. Subscriptions extending beyond the current year require a review by the learning coordinator. The coordinator records participation but does not replace the manager's purchase approval. Learning time must be agreed with the team.",
    ]),
    ("Business travel booking", [
        "Domestic business travel should be requested at least 14 calendar days before departure. A project sponsor must approve the trip before booking. The travel desk arranges approved tickets and accommodation through the company booking portal. The 14-day rule is a planning deadline, not the deadline for submitting a routine expense claim after buying something. Personal holidays are not covered by this section.",
        "For approved domestic trips, the hotel reimbursement ceiling is INR 4,500 per night before taxes. Any exception needs written approval from the finance director before booking. Travellers should keep invoices and check cancellation conditions. The travel desk can explain booking options, but cannot authorise an exception to the hotel ceiling. Emergency itinerary changes should be communicated to the project sponsor.",
    ]),
    ("Equipment incidents", [
        "A lost or stolen company laptop must be reported to the security team within one hour of discovery. Report the device identifier and the last known location if available. Do not wait for a manager to approve the report. The security team decides the containment steps. The employee must not attempt to recover a stolen device personally or share passwords with someone claiming to have found it.",
        "For an ordinary hardware failure with no suspected theft, contact the service desk and open an equipment ticket. Standard replacement accessories require cost-centre owner approval. This purchasing approval is different from the urgent security reporting requirement for a missing laptop. Personal accessories are not automatically reimbursed. The equipment team records returned assets and updates the inventory after a replacement.",
    ]),
    ("Meeting room reservations", [
        "Meeting rooms can be booked through the workplace calendar for a maximum of two hours per reservation. Longer workshops require approval from the workplace coordinator. The organiser should release a reservation when the meeting is cancelled. Remote-work approval does not reserve a meeting room automatically. Rooms with specialist video equipment should be selected only when that equipment is needed.",
        "If the organiser has not arrived within 15 minutes of the reservation start, the room may be released to another team. Participants should leave the room ready for the next meeting and remove confidential material from whiteboards. The workplace coordinator manages scheduling conflicts. This section sets room-use rules only; it does not define paid holiday entitlement or employee working-hour contracts.",
    ]),
    ("Visitor access", [
        "A host must register an external visitor at least one working day before the visit. Reception issues a temporary badge after checking the registration. Visitors must remain with their employee host in restricted areas. A meeting room invitation alone does not create building access. The visitor badge must be returned at reception before departure. Staff should not lend their own access badge to a guest.",
        "Deliveries should be directed to the designated receiving desk. Couriers are not automatically permitted into employee work areas. The host is responsible for informing reception about a cancelled visit. The facilities team maintains the guest register under the applicable records policy. This visitor procedure does not authorise disclosure of customer documents to a visitor, even when they are a business partner.",
    ]),
    ("Training event travel", [
        "Travel to an approved external training event uses the business travel booking process. The course fee counts toward the annual learning budget, but approved travel costs are recorded separately as travel expenses. Both the manager's learning approval and the project sponsor's travel approval are required when an event involves a course purchase and business travel. One approval does not replace the other.",
        "Employees attending a virtual course do not receive a travel allowance simply because the provider is based in another city. When an in-person event is cancelled, notify the learning coordinator and travel desk promptly so they can check refund terms. A refund should be recorded against the original expense category. Participation certificates should be added to the employee's learning record after the event.",
    ]),
]

CASES = [
    ("How long do I have to claim ordinary expenses?", [(1, "30 calendar days")]),
    ("What proof is required for a routine reimbursement?", [(1, "itemised receipt")]),
    ("Who approves routine claims above 5000 rupees?", [(1, "department manager")]),
    ("When are approved routine expenses paid?", [(1, "next monthly payroll cycle")]),
    ("How frequently can I work from home and who agrees to it?", [(2, "two days"), (2, "team lead")]),
    ("What are the core collaboration hours?", [(2, "10:00 AM to 3:00 PM")]),
    ("What connection should I use on my company laptop outside the office?", [(2, "approved VPN")]),
    ("What is the yearly professional development allowance?", [(3, "INR 12,000")]),
    ("Who signs off a course before it is bought?", [(3, "manager must approve")]),
    ("Can unused learning funds roll into the following year?", [(3, "does not carry forward")]),
    ("How far ahead should a domestic work trip be requested?", [(4, "14 calendar days")]),
    ("Who authorises a business trip before tickets are booked?", [(4, "project sponsor")]),
    ("What is the domestic hotel limit and who can approve an exception?", [(4, "INR 4,500"), (4, "finance director")]),
    ("My company laptop was stolen. When and to whom should I report it?", [(5, "within one hour"), (5, "security team")]),
    ("Who approves buying standard replacement accessories?", [(5, "cost-centre owner")]),
    ("What is the longest ordinary meeting-room booking?", [(6, "maximum of two hours")]),
    ("How late can an organiser arrive before the room is released?", [(6, "15 minutes")]),
    ("How much notice is needed to register a guest?", [(7, "one working day")]),
    ("Can a visitor use my access badge?", [(7, "should not lend")]),
    ("Does attending a virtual course qualify me for a travel allowance?", [(8, "do not receive a travel allowance")]),
    ("Who approves remote working and who approves a learning purchase?", [(2, "team lead"), (3, "manager must approve")]),
    ("Compare the expense submission deadline with the advance travel request deadline.", [(1, "30 calendar days"), (4, "14 calendar days")]),
    ("Does the course fee or the trip cost count toward my learning budget?", [(8, "course fee counts"), (8, "recorded separately")]),
    ("What approvals do I need for travelling to a paid training event?", [(8, "Both the manager's learning approval")]),
    ("How many paid holiday days does each employee receive?", []),
    ("What is the parental leave entitlement?", []),
    ("How large is the annual salary increase?", []),
]


def benchmark_pdf():
    output = BytesIO()
    canvas = Canvas(output, invariant=1)
    for page, (title, paragraphs) in enumerate(SECTIONS, 1):
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(45, 780, title)
        y = 744
        canvas.setFont("Helvetica", 11)
        for paragraph in paragraphs:
            for line in wrap(paragraph, 88):
                canvas.drawString(45, y, line)
                y -= 17
            y -= 18
        canvas.setFont("Helvetica", 9)
        canvas.drawString(45, 40, f"Fictional evaluation handbook | Page {page}")
        canvas.showPage()
    canvas.save()
    return output.getvalue()
