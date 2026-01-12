from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)

# Define Constants
DEFAULT_FONT_SIZE = 10
HEADING_FONT_SIZE = 14
TITLE_FONT_SIZE = 18
SPACE_AFTER_HEADING = 12
SPACE_AFTER_TITLE = 30
TABLE_HEADER_BG = colors.grey
TABLE_HEADER_TEXT_COLOR = colors.whitesmoke
TABLE_ROW_BG = colors.beige
TABLE_GRID_COLOR = colors.black


def _get_common_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=TITLE_FONT_SIZE,
        spaceAfter=SPACE_AFTER_TITLE,
        alignment=1  # Center alignment
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=HEADING_FONT_SIZE,
        spaceAfter=SPACE_AFTER_HEADING
    )
    return styles, title_style, heading_style


def _get_table_style(header_cols, row_cols):
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), DEFAULT_FONT_SIZE),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), TABLE_ROW_BG),
        ('GRID', (0, 0), (-1, -1), 1, TABLE_GRID_COLOR),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ])


def generate_attendance_pdf(student, attendance_logs):
    """Generate PDF content for student attendance report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        story.append(Paragraph("Student Attendance Report", title_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Student Information", heading_style))
        student_info = [
            ["Name:", student["name"]],
            ["Class:", student["class"]],
            ["Student ID:", str(student["id"])],
            ["Fingerprint ID:", str(student["fingerprint_id"]) if student["fingerprint_id"] else "Not assigned"]
        ]
        
        student_table = Table(student_info, colWidths=[1.5*inch, 3*inch])
        student_table.setStyle(_get_table_style(2, 2))
        story.append(student_table)
        story.append(Spacer(1, 20))
        
        total_days = len(attendance_logs)
        story.append(Paragraph(f"Attendance Summary ({total_days} days recorded)", heading_style))
        
        if attendance_logs:
            table_data = [["Date", "Scans", "First Scan", "Last Scan"]]
            
            for log in attendance_logs:
                table_data.append([
                    log["date"].strftime("%Y-%m-%d"),
                    str(log["scan_count"]),
                    log["first_scan"].strftime("%H:%M:%S"),
                    log["last_scan"].strftime("%H:%M:%S")
                ])
            
            attendance_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 1.2*inch, 1.2*inch])
            attendance_table.setStyle(_get_table_style(4, 4))
            story.append(attendance_table)
        else:
            story.append(Paragraph("No attendance records found.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.exception("Error generating student attendance PDF: %s", e)
        raise


def generate_class_attendance_pdf(class_name, students, date):
    """Generate PDF content for class attendance report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        story.append(Paragraph(f"Class Attendance Report - {class_name} ({date.strftime('%Y-%m-%d')})", title_style))
        story.append(Spacer(1, 20))
        
        if students:
            table_data = [["Name", "Status"]]
            
            for student in students:
                table_data.append([
                    student["name"],
                    student["status"]
                ])
            
            attendance_table = Table(table_data, colWidths=[2*inch, 1.5*inch])
            attendance_table.setStyle(_get_table_style(2, 2))
            story.append(attendance_table)
        else:
            story.append(Paragraph("No students found for this class.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        logger.exception("Error generating class attendance PDF: %s", e)
        raise
