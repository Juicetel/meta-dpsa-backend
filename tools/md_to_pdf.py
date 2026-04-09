"""
Tool: md_to_pdf.py
Responsibility: Convert Markdown files to professional PDF documents.
WAT Role: Tools layer -- deterministic execution.
"""

import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
import markdown
import re


def convert_md_to_pdf(md_file_path: str, output_pdf_path: str = None) -> str:
    """
    Convert a Markdown file to a styled PDF document.

    Args:
        md_file_path: Path to the markdown file
        output_pdf_path: Optional path for output PDF (defaults to same name with .pdf extension)

    Returns:
        Path to the generated PDF file
    """
    md_path = Path(md_file_path)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_file_path}")

    # Determine output path
    if output_pdf_path is None:
        output_pdf_path = md_path.with_suffix('.pdf')
    else:
        output_pdf_path = Path(output_pdf_path)

    # Read markdown content
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Create PDF
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=16,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
        borderColor=colors.HexColor('#3498db'),
        borderRadius=0
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )

    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=20,
        spaceAfter=6
    )

    # Parse markdown and build PDF elements
    story = []
    lines = md_content.split('\n')
    i = 0
    is_first_heading = True
    in_table = False
    table_data = []

    while i < len(lines):
        line = lines[i].strip()

        # Skip horizontal rules
        if line.startswith('---'):
            story.append(Spacer(1, 0.2*inch))
            i += 1
            continue

        # Title (first H1)
        if line.startswith('# ') and is_first_heading:
            text = line[2:].strip()
            story.append(Paragraph(text, title_style))
            story.append(Spacer(1, 0.3*inch))
            is_first_heading = False
            i += 1
            continue

        # H1
        if line.startswith('# '):
            text = line[2:].strip()
            story.append(Paragraph(text, h1_style))
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        # H2
        if line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, h2_style))
            i += 1
            continue

        # H3
        if line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, h3_style))
            i += 1
            continue

        # Table detection (simple markdown tables)
        if '|' in line and not in_table:
            in_table = True
            table_data = []

        if in_table:
            if '|' in line and not line.replace('|', '').replace('-', '').strip() == '':
                # Parse table row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                table_data.append(cells)
                i += 1
                continue
            elif line.replace('|', '').replace('-', '').strip() == '':
                # Skip separator line
                i += 1
                continue
            else:
                # End of table
                if table_data:
                    # Create table
                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))
                in_table = False
                table_data = []
                continue

        # Bullet points
        if line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            # Convert markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            text = text.replace('⭐', '★')
            text = text.replace('✅', '✓')
            text = text.replace('⚠️', '⚠')
            story.append(Paragraph(f'• {text}', bullet_style))
            i += 1
            continue

        # Numbered lists
        if re.match(r'^\d+\.\s+', line):
            text = re.sub(r'^\d+\.\s+', '', line)
            # Convert markdown formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            text = text.replace('⭐', '★')
            text = text.replace('✅', '✓')
            text = text.replace('⚠️', '⚠')
            story.append(Paragraph(f'{line.split(".")[0]}. {text}', bullet_style))
            i += 1
            continue

        # Regular paragraph
        if line and not line.startswith('#'):
            # Convert markdown formatting to reportlab
            text = line
            # Handle bold (**text**)
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            # Handle italic (*text* or _text_)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
            # Replace emojis with safe equivalents
            text = text.replace('⭐', '★')
            text = text.replace('✅', '✓')
            text = text.replace('⚠️', '⚠')

            story.append(Paragraph(text, body_style))
            i += 1
            continue

        # Empty line
        if not line:
            story.append(Spacer(1, 0.1*inch))
            i += 1
            continue

        i += 1

    # Build PDF
    doc.build(story)

    return str(output_pdf_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python md_to_pdf.py <markdown_file> [output_pdf]")
        sys.exit(1)

    md_file = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = convert_md_to_pdf(md_file, output_pdf)
        print(f"PDF generated successfully: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
