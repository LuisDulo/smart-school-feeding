# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
    Table, TableStyle, HRFlowable
)

NAVY = colors.HexColor('#1A3A5C')
GREEN = colors.HexColor('#1A6E3C')
GREY = colors.HexColor('#6B7280')
LIGHT_BG = colors.HexColor('#F7F9FC')

OUT = "Smart_School_Feeding_Features.pdf"

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    topMargin=20 * mm, bottomMargin=18 * mm,
    leftMargin=20 * mm, rightMargin=20 * mm,
    title="Smart School Feeding — Features Completed",
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'TitleCustom', parent=styles['Title'], textColor=NAVY,
    fontSize=22, leading=26, spaceAfter=2, alignment=TA_LEFT,
)
subtitle_style = ParagraphStyle(
    'SubtitleCustom', parent=styles['Normal'], textColor=GREY,
    fontSize=10.5, leading=14, spaceAfter=0,
)
meta_style = ParagraphStyle(
    'MetaCustom', parent=styles['Normal'], textColor=GREY,
    fontSize=9, leading=13,
)
section_style = ParagraphStyle(
    'SectionCustom', parent=styles['Heading2'], textColor=NAVY,
    fontSize=13.5, leading=17, spaceBefore=14, spaceAfter=6,
)
body_style = ParagraphStyle(
    'BodyCustom', parent=styles['Normal'], fontSize=10, leading=14.5,
    textColor=colors.HexColor('#1F2937'),
)
bullet_style = ParagraphStyle(
    'BulletCustom', parent=body_style, spaceAfter=3,
)
strong_label_style = ParagraphStyle(
    'StrongLabel', parent=body_style, textColor=NAVY,
)

story = []

# Header block
story.append(Paragraph("Smart School Feeding Management System", title_style))
story.append(Paragraph("Features Completed — Project Status Update", subtitle_style))
story.append(Spacer(1, 8))
story.append(HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=8))

meta_table = Table(
    [
        ["Student:", "Luis Enrique Okal Dulo (Adm: 169685)"],
        ["Supervisor:", "Allan Vikiru"],
        ["Partner Organisation:", "Webmasters Kenya"],
        ["Programme:", "BSc Informatics and Computer Science, Strathmore University"],
        ["Stack:", "Django REST Framework · React Native/Expo · React.js · PostgreSQL · "
                    "scikit-learn · M-Pesa Daraja API"],
    ],
    colWidths=[110, 380],
)
meta_table.setStyle(TableStyle([
    ('FONTSIZE', (0, 0), (-1, -1), 9.5),
    ('TEXTCOLOR', (0, 0), (0, -1), NAVY),
    ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#374151')),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ('TOPPADDING', (0, 0), (-1, -1), 0),
    ('LEFTPADDING', (0, 0), (-1, -1), 0),
]))
story.append(meta_table)
story.append(Spacer(1, 4))
story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#E5E7EB'), spaceAfter=4))


def section(title):
    story.append(Paragraph(title, section_style))


def bullets(items):
    flow_items = []
    for it in items:
        flow_items.append(ListItem(Paragraph(it, bullet_style), spaceAfter=3, bulletColor=GREEN))
    story.append(ListFlowable(flow_items, bulletType='bullet', start='•',
                               leftIndent=14, bulletFontSize=8))


# Sections
section("Authentication &amp; Accounts")
bullets([
    "JWT-based login for all roles (parent, student, kitchen staff, bursar, admin).",
    "Self-registration (parent/student) still available in the mobile app.",
    "<b>Admin-driven account creation</b>: admins can create student accounts (with starting balance) "
    "and parent accounts directly from the dashboard, and link them to each other.",
    "Real parent&#8596;child relationship (many-to-many &#8220;guardians&#8221;), so a parent can have "
    "multiple children and a child can have multiple guardians.",
    "Role-based permissions enforced end-to-end (admin / bursar / kitchen / parent / student each "
    "see only what they are allowed to).",
])

section("Parent Features (Mobile App)")
bullets([
    "View child's real-time meal account balance.",
    "Top up balance via M-Pesa STK Push (Daraja API, sandbox-tested).",
    "View payment / top-up history.",
    "<b>View meal consumption history</b> &#8212; what their child ate, cost, date, and which kitchen "
    "staff served it.",
    "<b>Raise support issues / complaints</b> (balance, meal quality, technical, other) and track status "
    "(open &#8594; in progress &#8594; resolved) with the admin's reply.",
    "<b>Apply for credit</b> &#8212; request a higher spending limit so their child can keep eating on "
    "credit if funds run low; this raises an approved overdraft ceiling only, never fakes real balance.",
    "Low-balance alerts.",
])

section("Kitchen Staff Features (Mobile + Dashboard)")
bullets([
    "Search / look up any student by name or ID.",
    "<b>Menu-based meal serving</b>: pick which food items a student is taking (e.g. Rice, Beans, Sukuma) "
    "&#8212; price is computed automatically as the sum.",
    "<b>Search meal combinations</b>: named bundles (e.g. &#8220;Lunch Special&#8221;) auto-select all "
    "their items and show the combined price instantly, on top of picking individual items.",
    "Prevents double-serving the same student twice in one day.",
    "Enforces balance / credit limits before serving (blocks or allows based on approved overdraft).",
    "&#8220;Served by&#8221; is automatically recorded via the logged-in kitchen account's name and "
    "email &#8212; cannot be spoofed.",
])

section("Admin Dashboard")
bullets([
    "Full overview dashboard: meals served today, KES collected, low-balance students, pending anomaly "
    "flags, 7-day collection chart, demand forecast preview.",
    "Student balances table (all students, sortable by balance).",
    "<b>Menu Management</b>: add / edit / remove priced food items; create and manage named meal "
    "combinations.",
    "<b>Account Management</b>: create student &amp; parent accounts, link / unlink guardians to students.",
    "<b>Credit Requests queue</b>: review parent overdraft requests, approve (raises spending limit) or "
    "reject.",
    "<b>Support Issues queue</b>: view and resolve parent-raised complaints with notes.",
    "Meal Distribution log: daily list of every meal served, itemised with cost and server identity.",
    "Demand forecasting (generate &amp; view predictions).",
    "Anomaly flag review and resolution.",
    "CSV reports (payments, meal distribution, anomalies, term summary).",
])

section("Bursar Dashboard")
bullets([
    "Student balances, meal distribution log, demand forecast (same visibility as admin).",
    "<b>Credit Requests queue</b> (view-only &#8212; financial oversight; only admin can approve/reject).",
    "<b>Support Issues queue</b> (can resolve, same as admin).",
    "Anomaly flags and CSV reports.",
    "Sidebar now shows only the pages relevant to their role (no more confusing access-denied pages).",
])

section("Machine Learning")
bullets([
    "<b>Demand forecasting</b> &#8212; Linear Regression model predicting daily meal counts and cost for "
    "the coming week.",
    "<b>Anomaly detection</b> &#8212; Isolation Forest model flagging suspicious payment transactions for "
    "bursar/admin review.",
])

section("Payments")
bullets([
    "M-Pesa Daraja STK Push integration (sandbox), tested live end-to-end via an ngrok tunnel including "
    "the callback path.",
    "Idempotent payment callback handling (a retried/duplicate Safaricom callback cannot double-credit "
    "an account).",
    "Overdraft/credit system layered on top of real balance (never fakes real money &#8212; only a real "
    "M-Pesa top-up increases actual balance).",
])

section("Quality Assurance")
bullets([
    "77 automated backend tests, all passing.",
    "Full live end-to-end verification pass completed: parent-child linking, issue reporting reaching "
    "the dashboard, credit requests reaching admin/bursar, menu-priced serving syncing across mobile "
    "and dashboard, and the real M-Pesa payment flow &#8212; all confirmed working together correctly.",
])

story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor('#E5E7EB')))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Generated as a project status summary for supervisor/stakeholder update.",
    ParagraphStyle('Footer', parent=meta_style, alignment=TA_LEFT)
))

doc.build(story)
print("wrote", OUT)
