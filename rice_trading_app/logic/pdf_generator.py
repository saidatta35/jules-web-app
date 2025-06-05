import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os # For standalone __main__ path fallback

# DATABASE_PATH = "../database/rice_trader.db" # No longer module-level constant

def get_db_connection(db_path=None): # Added db_path parameter
    """Establishes a connection to the SQLite database."""
    if not db_path: # Fallback for standalone or direct test
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
        # Ensure dir exists for standalone test
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            # from ..database.database_setup import create_tables # Consider for full standalone
            # create_tables(db_path)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e} (Path: {db_path})")
        return None

def generate_gate_pass_pdf(gate_pass_id, file_path, db_path): # Added db_path
    """Generates a PDF for a given Gate Pass ID."""
    conn = get_db_connection(db_path) # Pass db_path
    if not conn:
        return False, "Database connection failed."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM GatePasses WHERE gate_pass_id = ?", (gate_pass_id,))
        gp_data = cursor.fetchone()

        if not gp_data:
            return False, f"Gate Pass ID {gate_pass_id} not found."

        cursor.execute("SELECT * FROM GatePassOrderDetails WHERE gate_pass_id = ?", (gate_pass_id,))
        order_items = cursor.fetchall()

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                topMargin=0.5*inch, bottomMargin=0.5*inch,
                                leftMargin=0.75*inch, rightMargin=0.75*inch)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = styles['h1']
        title_style.alignment = 1 # Center

        header_style = styles['h3']
        normal_style = styles['Normal']
        normal_right_style = ParagraphStyle(name='NormalRight', parent=normal_style, alignment=2) # Right align


        story.append(Paragraph("Gate Pass", title_style))
        story.append(Spacer(1, 0.25*inch))

        # General Info
        info_data = [
            [Paragraph(f"<b>Gate Pass ID:</b> {gp_data['gate_pass_id']}", normal_style),
             Paragraph(f"<b>Date:</b> {gp_data['date']}", normal_style)],
            [Paragraph(f"<b>Party Name:</b> {gp_data['party_name']}", normal_style),
             Paragraph(f"<b>Vehicle No:</b> {gp_data['vehicle_number'] or 'N/A'}", normal_style)],
            [Paragraph(f"<b>Address:</b> {gp_data['address'] or 'N/A'}", normal_style),
             Paragraph(f"<b>Broker:</b> {gp_data['broker_name'] or 'N/A'}", normal_style)],
        ]
        info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2*inch))

        # Order Details Table
        story.append(Paragraph("<u>Order Details:</u>", header_style))
        story.append(Spacer(1, 0.1*inch))

        table_data = [["SNo", "Lot Name", "Brand", "Bags", "Wt/Bag\n(Kg)", "Total Wt\n(Qtl)", "Price/Qtl\n(₹)", "Total\n(₹)"]]
        s_no = 1
        total_quintals_sum = 0.0
        total_bags_sum = 0
        grand_item_total_price = 0.0

        for item in order_items:
            total_wt_qtl = (item["num_bags"] * item["weight_per_bag_kg"]) / 100.0
            item_total_val = total_wt_qtl * item["price_per_quintal"]
            table_data.append([
                s_no,
                Paragraph(item["lot_name"], normal_style),
                Paragraph(item["brand"] or "N/A", normal_style),
                item["num_bags"],
                f"{item['weight_per_bag_kg']:.2f}",
                f"{total_wt_qtl:.2f}",
                f"{item['price_per_quintal']:.2f}",
                f"{item_total_val:.2f}",
            ])
            s_no += 1
            total_quintals_sum += total_wt_qtl
            total_bags_sum += item["num_bags"]
            grand_item_total_price += item_total_val

        order_table = Table(table_data, colWidths=[0.4*inch, 1.5*inch, 1*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.9*inch])
        order_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'), # SNo center
            ('ALIGN', (3,1), (-1,-1), 'RIGHT'), # Numeric cols right
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 8), # Header padding
            ('TOPPADDING', (0,0), (-1,0), 8),    # Header padding
            ('BOTTOMPADDING', (0,1), (-1,-1), 4), # Row padding
            ('TOPPADDING', (0,1), (-1,-1), 4),    # Row padding
        ]))
        story.append(order_table)
        story.append(Spacer(1, 0.2*inch))

        # Charges & Totals
        amali_charge_rate = gp_data["amali_charge_per_quintal"]
        bag_charge_rate = gp_data["bag_charge_per_bag"]
        total_amali_charges_calc = total_quintals_sum * amali_charge_rate
        total_bag_charges_calc = total_bags_sum * bag_charge_rate

        # Stored grand total (should be used as primary)
        stored_grand_total = gp_data["grand_total"]

        summary_data = [
            [Paragraph("Total Item Value:", normal_style), Paragraph(f"₹{grand_item_total_price:.2f}", normal_right_style)],
            [Paragraph(f"Amali Charges ({total_quintals_sum:.2f} Qtl @ ₹{amali_charge_rate:.2f}/Qtl):", normal_style), Paragraph(f"₹{total_amali_charges_calc:.2f}", normal_right_style)],
            [Paragraph(f"Bag Charges ({total_bags_sum} Bags @ ₹{bag_charge_rate:.2f}/Bag):", normal_style), Paragraph(f"₹{total_bag_charges_calc:.2f}", normal_right_style)],
            [Paragraph("<b>Grand Total:</b>", normal_style), Paragraph(f"<b>₹{stored_grand_total:.2f}</b>", normal_right_style)],
        ]
        summary_table = Table(summary_data, colWidths=[5.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Receiver's Signature: _______________________", normal_style))


        doc.build(story)
        return True, "Gate Pass PDF generated successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    except Exception as e:
        return False, f"An error occurred: {e}"
    finally:
        if conn:
            conn.close()

def generate_transaction_summary_pdf(gate_pass_id, file_path, db_path): # Added db_path
    """Generates a PDF for the Transaction Summary (Dr/Cr)."""
    conn = get_db_connection(db_path) # Pass db_path
    if not conn:
        return False, "Database connection failed."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM GatePasses WHERE gate_pass_id = ?", (gate_pass_id,))
        gp_data = cursor.fetchone()

        if not gp_data:
            return False, f"Gate Pass ID {gate_pass_id} not found."

        doc = SimpleDocTemplate(file_path, pagesize=letter,
                                topMargin=0.5*inch, bottomMargin=0.5*inch,
                                leftMargin=0.75*inch, rightMargin=0.75*inch)
        story = []
        styles = getSampleStyleSheet()
        title_style = styles['h1']
        title_style.alignment = 1 # Center
        header_style = styles['h3']
        normal_style = styles['Normal']

        story.append(Paragraph("Transaction Summary (Debit/Credit)", title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"<b>Gate Pass ID:</b> {gp_data['gate_pass_id']}", normal_style))
        story.append(Paragraph(f"<b>Date:</b> {gp_data['date']}", normal_style))
        story.append(Paragraph(f"<b>Party Name:</b> {gp_data['party_name']}", normal_style))
        story.append(Spacer(1, 0.2*inch))

        # --- Credit Side ---
        story.append(Paragraph("<u>CREDIT (Party's A/c / Sales Revenue)</u>", header_style))
        story.append(Spacer(1, 0.1*inch))

        credit_table_data = [["Description", "Amount (Cr.) ₹"]]
        cursor.execute("SELECT * FROM GatePassOrderDetails WHERE gate_pass_id = ?", (gate_pass_id,))
        order_items = cursor.fetchall()

        total_calculated_item_value = 0.0
        total_quintals_sum = 0.0
        total_bags_sum = 0

        for item in order_items:
            item_total_quintals = (item["num_bags"] * item["weight_per_bag_kg"]) / 100.0
            item_total_price = item_total_quintals * item["price_per_quintal"]
            desc = f"Sale: {item['brand'] or 'N/A'} Rice, Lot: {item['lot_name']} ({item['num_bags']} bags)"
            credit_table_data.append([Paragraph(desc, normal_style), f"{item_total_price:.2f}"])
            total_calculated_item_value += item_total_price
            total_quintals_sum += item_total_quintals
            total_bags_sum += item["num_bags"]

        amali_charge_rate = gp_data["amali_charge_per_quintal"]
        bag_charge_rate = gp_data["bag_charge_per_bag"]
        total_amali_charges_calc = total_quintals_sum * amali_charge_rate
        total_bag_charges_calc = total_bags_sum * bag_charge_rate

        if total_amali_charges_calc > 0:
            credit_table_data.append([Paragraph("Amali Charges", normal_style), f"{total_amali_charges_calc:.2f}"])
        if total_bag_charges_calc > 0:
            credit_table_data.append([Paragraph("Bag Charges", normal_style), f"{total_bag_charges_calc:.2f}"])

        credit_table_data.append([Paragraph("<b>Grand Total (Credit)</b>", normal_style), Paragraph(f"<b>{gp_data['grand_total']:.2f}</b>", normal_style)])

        credit_table = Table(credit_table_data, colWidths=[5.5*inch, 1.5*inch])
        credit_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'), # Amount column right
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        story.append(credit_table)
        story.append(Spacer(1, 0.2*inch))

        # --- Debit Side ---
        story.append(Paragraph("<u>DEBIT (Inventory Reduction / COGS)</u>", header_style))
        story.append(Spacer(1, 0.1*inch))

        debit_table_data = [["Lot Name", "Qty (Qtls)", "Price/Qtl (₹)", "Amount (Dr.) ₹"]]
        cursor.execute("""
            SELECT lot_name, quantity_quintals, price_per_quintal, debit_amount
            FROM Transactions
            WHERE gate_pass_id = ? AND debit_amount > 0 AND description LIKE 'Sale of goods%'
        """, (gate_pass_id,))
        debit_transactions = cursor.fetchall()

        total_debit_amount = 0.0
        for trans in debit_transactions:
            debit_table_data.append([
                Paragraph(trans["lot_name"], normal_style),
                f"{trans['quantity_quintals']:.2f}",
                f"{trans['price_per_quintal']:.2f}",
                f"{trans['debit_amount']:.2f}"
            ])
            total_debit_amount += trans["debit_amount"]

        debit_table_data.append([Paragraph("<b>Total (Debit/COGS)</b>", normal_style), "", "", Paragraph(f"<b>{total_debit_amount:.2f}</b>", normal_style)])

        debit_table = Table(debit_table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        debit_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'), # Numeric cols right
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('SPAN', (0, -1), (2, -1)), # Span for Total Debit label
        ]))
        story.append(debit_table)

        doc.build(story)
        return True, "Transaction Summary PDF generated successfully."

    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    except Exception as e:
        return False, f"An error occurred: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Example Usage (for testing - create dummy data or use existing)
    # Ensure you have a database rice_trader.db in ../database/ with some data for testing
    print("Attempting to generate sample PDFs (if example IDs are valid)...")

    # Standalone DB path determination (relative to this file)
    STANDALONE_DB_PATH_PDF = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
    REPORTS_DIR_PDF = os.path.join(os.path.dirname(__file__), "..", "reports")

    if not os.path.exists(REPORTS_DIR_PDF):
        os.makedirs(REPORTS_DIR_PDF, exist_ok=True)

    # Example: Test Gate Pass PDF (replace '1' with a valid ID from your test DB)
    # To run this test, you'd need to ensure STANDALONE_DB_PATH_PDF points to a DB with data.
    # And potentially call create_tables from database_setup if it's a fresh test.
    # from ..database.database_setup import create_tables
    # db_dir = os.path.dirname(STANDALONE_DB_PATH_PDF)
    # if not os.path.exists(db_dir): os.makedirs(db_dir, exist_ok=True)
    # create_tables(STANDALONE_DB_PATH_PDF) # To ensure tables exist for test

    # print(f"Using DB path for standalone PDF test: {STANDALONE_DB_PATH_PDF}")

    # gp_id_to_test = 1
    # gp_file_path = os.path.join(REPORTS_DIR_PDF, f"gate_pass_{gp_id_to_test}_test.pdf")
    # success_gp, message_gp = generate_gate_pass_pdf(gp_id_to_test, gp_file_path, STANDALONE_DB_PATH_PDF)
    # if success_gp:
    #     print(f"Gate Pass PDF: {message_gp} (saved to {gp_file_path})")
    # else:
    #     print(f"Gate Pass PDF Error: {message_gp}")

    # ts_file_path = os.path.join(REPORTS_DIR_PDF, f"transaction_summary_{gp_id_to_test}_test.pdf")
    # success_ts, message_ts = generate_transaction_summary_pdf(gp_id_to_test, ts_file_path, STANDALONE_DB_PATH_PDF)
    # if success_ts:
    #     print(f"Transaction Summary PDF: {message_ts} (saved to {ts_file_path})")
    # else:
    #     print(f"Transaction Summary PDF Error: {message_ts}")

    print("PDF generation script `if __name__ == '__main__'` finished. Uncomment and adapt test calls as needed.")
