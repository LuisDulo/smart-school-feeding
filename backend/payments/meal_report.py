"""
Downloadable meal report for a student's meal account.

build_report() gathers the data (monthly summary + every meal served in the
period), and render_csv() / render_pdf() turn it into a file. The monthly
summary logic is shared with the on-screen Monthly Report view so the numbers
a parent sees and the numbers they download always match.
"""
import calendar
import csv
import io
import re
from datetime import date

from fpdf import FPDF
from fpdf.fonts import FontFace

from meals.models import MealDistributionEvent, PaymentTransaction


def monthly_breakdown(meal_account, months_count):
    """Per-month meals, spend and top-ups for the last `months_count` months
    (including the current one), oldest first."""
    today = date.today()
    monthly_data = []

    for i in range(months_count - 1, -1, -1):
        month_date = date(today.year, today.month, 1)
        for _ in range(i):
            if month_date.month == 1:
                month_date = date(month_date.year - 1, 12, 1)
            else:
                month_date = date(month_date.year, month_date.month - 1, 1)

        last_day = calendar.monthrange(month_date.year, month_date.month)[1]
        month_end = date(month_date.year, month_date.month, last_day)

        payments = PaymentTransaction.objects.filter(
            meal_account=meal_account,
            status='confirmed',
            created_at__date__gte=month_date,
            created_at__date__lte=month_end,
        )
        total_topped_up = sum(p.amount_cents for p in payments) / 100

        meals = MealDistributionEvent.objects.filter(
            meal_account=meal_account,
            meal_date__gte=month_date,
            meal_date__lte=month_end,
        )
        meals_cost = sum(m.amount_cents for m in meals) / 100

        monthly_data.append({
            'month': month_date.strftime('%B %Y'),
            'month_short': month_date.strftime('%b'),
            'year': month_date.year,
            'month_start': month_date,
            'total_topped_up_ksh': total_topped_up,
            'num_top_ups': payments.count(),
            'meals_collected': meals.count(),
            'meals_cost_ksh': meals_cost,
            'avg_cost_per_day': round(meals_cost / last_day, 2),
        })
    return monthly_data


def build_report(meal_account, months_count):
    monthly = monthly_breakdown(meal_account, months_count)
    start = monthly[0]['month_start']
    today = date.today()

    events = (MealDistributionEvent.objects
              .filter(meal_account=meal_account, meal_date__gte=start,
                      meal_date__lte=today)
              .select_related('recorded_by')
              .prefetch_related('items')
              .order_by('meal_date', 'id'))
    meals = [{
        'date': e.meal_date,
        'items': ', '.join(i.name for i in e.items.all()) or 'Meal',
        'amount_ksh': e.amount_cents / 100,
        'served_by': e.recorded_by.full_name if e.recorded_by else '',
    } for e in events]

    student = meal_account.student
    return {
        'student_name': student.full_name,
        'school_name': student.school.name if student.school else '',
        'period_start': start,
        'period_end': today,
        'generated_on': today,
        'months': months_count,
        'current_balance_ksh': meal_account.balance_cents / 100,
        'monthly': monthly,
        'meals': meals,
        'total_meals': sum(m['meals_collected'] for m in monthly),
        'total_spent_ksh': sum(m['meals_cost_ksh'] for m in monthly),
        'total_topped_up_ksh': sum(m['total_topped_up_ksh'] for m in monthly),
    }


def report_filename(data, extension):
    slug = re.sub(r'[^a-z0-9]+', '-', data['student_name'].lower()).strip('-') or 'student'
    return f"meal-report-{slug}-{data['generated_on'].isoformat()}.{extension}"


def _money(value):
    return f"{value:,.2f}"


def render_csv(data):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['Meal Report'])
    w.writerow(['Student', data['student_name']])
    w.writerow(['School', data['school_name']])
    w.writerow(['Period', f"{data['period_start']:%d %b %Y} to {data['period_end']:%d %b %Y}"])
    w.writerow(['Generated', f"{data['generated_on']:%d %b %Y}"])
    w.writerow(['Current balance (KES)', _money(data['current_balance_ksh'])])
    w.writerow([])
    w.writerow(['Monthly summary'])
    w.writerow(['Month', 'Meals collected', 'Spent (KES)', 'Topped up (KES)',
                'Top-ups', 'Average spend per day (KES)'])
    for m in data['monthly']:
        w.writerow([m['month'], m['meals_collected'], _money(m['meals_cost_ksh']),
                    _money(m['total_topped_up_ksh']), m['num_top_ups'],
                    _money(m['avg_cost_per_day'])])
    w.writerow(['Total', data['total_meals'], _money(data['total_spent_ksh']),
                _money(data['total_topped_up_ksh']), '', ''])
    w.writerow([])
    w.writerow(['Meals served'])
    w.writerow(['Date', 'Items', 'Amount (KES)', 'Served by'])
    for meal in data['meals']:
        w.writerow([f"{meal['date']:%Y-%m-%d}", meal['items'],
                    _money(meal['amount_ksh']), meal['served_by']])
    # BOM so Excel opens the UTF-8 file correctly
    return ('﻿' + buf.getvalue()).encode('utf-8')


def _latin1(text):
    """fpdf2's built-in fonts only cover Latin-1; replace anything else."""
    return str(text).encode('latin-1', 'replace').decode('latin-1')


class _ReportPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, 'Smart School Feeding Management System', align='L')
        self.cell(0, 6, f'Page {self.page_no()}/{{nb}}', align='R')


def render_pdf(data):
    pdf = _ReportPDF(format='A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Header band
    pdf.set_fill_color(26, 58, 92)
    pdf.rect(0, 0, 210, 30, style='F')
    pdf.set_xy(12, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 8, 'Meal Report', new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(12)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, _latin1(f"{data['student_name']}  -  {data['school_name']}"))

    # Details (reset the fill colour so table body cells stay unfilled)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(40, 40, 40)
    pdf.set_xy(12, 38)
    pdf.set_font('Helvetica', '', 10)
    details = [
        ('Period', f"{data['period_start']:%d %b %Y} to {data['period_end']:%d %b %Y}"),
        ('Generated', f"{data['generated_on']:%d %b %Y}"),
        ('Current balance', f"KES {_money(data['current_balance_ksh'])}"),
    ]
    for label, value in details:
        pdf.set_x(12)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(38, 6, label)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, _latin1(value), new_x='LMARGIN', new_y='NEXT')

    def section(title):
        pdf.ln(4)
        pdf.set_x(12)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(26, 58, 92)
        pdf.cell(0, 8, title, new_x='LMARGIN', new_y='NEXT')
        pdf.set_text_color(40, 40, 40)

    heading_style = FontFace(emphasis='BOLD', color=(255, 255, 255),
                             fill_color=(26, 58, 92))
    bold = FontFace(emphasis='BOLD')

    def table(headers, rows, widths, aligns, total_row=None):
        pdf.set_x(12)
        pdf.set_font('Helvetica', '', 9)
        with pdf.table(col_widths=widths, text_align=aligns, line_height=6,
                       headings_style=heading_style, first_row_as_headings=True,
                       borders_layout='HORIZONTAL_LINES', padding=1) as t:
            head = t.row()
            for h in headers:
                head.cell(h)
            for r in rows:
                row = t.row()
                for cell in r:
                    row.cell(_latin1(cell))
            if total_row:
                row = t.row()
                for cell in total_row:
                    row.cell(_latin1(cell), style=bold)

    section('Monthly summary')
    table(
        ['Month', 'Meals', 'Spent (KES)', 'Topped up (KES)', 'Top-ups', 'Avg / day (KES)'],
        [[m['month'], m['meals_collected'], _money(m['meals_cost_ksh']),
          _money(m['total_topped_up_ksh']), m['num_top_ups'], _money(m['avg_cost_per_day'])]
         for m in data['monthly']],
        widths=(34, 18, 34, 38, 22, 34),
        aligns=('LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'),
        total_row=['Total', data['total_meals'], _money(data['total_spent_ksh']),
                   _money(data['total_topped_up_ksh']), '', ''],
    )

    section(f"Meals served ({len(data['meals'])})")
    if data['meals']:
        table(
            ['Date', 'Items', 'Amount (KES)', 'Served by'],
            [[f"{m['date']:%a %d %b %Y}", m['items'], _money(m['amount_ksh']), m['served_by']]
             for m in data['meals']],
            widths=(34, 72, 30, 44),
            aligns=('LEFT', 'LEFT', 'RIGHT', 'LEFT'),
        )
    else:
        pdf.set_x(12)
        pdf.cell(0, 8, 'No meals were recorded in this period.')

    return bytes(pdf.output())
