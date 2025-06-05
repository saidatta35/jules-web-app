import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from logic.pdf_generator import generate_transaction_summary_pdf # Corrected import path
import os

# DATABASE_PATH = "../database/rice_trader.db" # No longer used

def get_db_connection(db_path=None): # Added db_path
    """Establishes a connection to the SQLite database."""
    if not db_path: # Fallback for standalone
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            # Consider calling create_tables here for robust standalone testing
            # from ..database.database_setup import create_tables
            # create_tables(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not connect to database: {e} (Path: {db_path})")
        return None

def fetch_and_display_summary(gp_id_entry, main_display_frame, parent_window, db_path): # Added db_path
    """Fetches and displays the transaction summary for the given Gate Pass ID.
    Returns True if summary loaded successfully, False otherwise.
    """
    try:
        gate_pass_id = int(gp_id_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Gate Pass ID must be a valid number.", parent=parent_window)
        return False

    for widget in main_display_frame.winfo_children(): # Clear previous display
        widget.destroy()

    conn = get_db_connection(db_path) # Use db_path
    if not conn: return False

    try:
        cursor = conn.cursor()

        # --- Fetch Gate Pass General Info ---
        cursor.execute("SELECT * FROM GatePasses WHERE gate_pass_id = ?", (gate_pass_id,))
        gp_data = cursor.fetchone()

        if not gp_data:
            messagebox.showerror("Not Found", f"Gate Pass ID {gate_pass_id} not found.", parent=parent_window)
            conn.close()
            return False

        # --- Setup Display Structure within main_display_frame ---
        info_frame = ttk.Frame(main_display_frame, padding=5)
        info_frame.pack(fill="x", pady=5)
        ttk.Label(info_frame, text=f"Gate Pass ID: {gp_data['gate_pass_id']}", font=('Arial', 10, 'bold')).pack(side="left", padx=5)
        ttk.Label(info_frame, text=f"Date: {gp_data['date']}", font=('Arial', 10, 'bold')).pack(side="left", padx=5)

        party_name_label = ttk.Label(info_frame, text=f"Party: {gp_data['party_name']}", font=('Arial', 10, 'bold'))
        party_name_label.pack(side="left", padx=5)


        # PanedWindow to hold Credit and Debit sides
        paned_window = ttk.PanedWindow(main_display_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=5)

        credit_outer_frame = ttk.LabelFrame(paned_window, text="CREDIT (Party's A/c / Sales Revenue)", padding=10)
        debit_outer_frame = ttk.LabelFrame(paned_window, text="DEBIT (Inventory Reduction / COGS)", padding=10)

        paned_window.add(credit_outer_frame, weight=1)
        paned_window.add(debit_outer_frame, weight=1)

        # --- Populate Credit Side ---
        credit_tree = ttk.Treeview(credit_outer_frame, columns=("desc", "amount"), show="headings", height=8)
        credit_tree.heading("desc", text="Description")
        credit_tree.heading("amount", text="Amount (Cr.) ₹")
        credit_tree.column("desc", width=250)
        credit_tree.column("amount", width=100, anchor="e")
        credit_tree.pack(fill="both", expand=True)

        cursor.execute("SELECT * FROM GatePassOrderDetails WHERE gate_pass_id = ?", (gate_pass_id,))
        order_items = cursor.fetchall()

        total_calculated_item_value = 0.0
        total_quintals = 0.0
        total_bags = 0

        for item in order_items:
            item_total_quintals = (item["num_bags"] * item["weight_per_bag_kg"]) / 100.0
            item_total_price = item_total_quintals * item["price_per_quintal"]
            desc = f"Sale: {item['brand'] or 'N/A'} Rice, Lot: {item['lot_name']} ({item['num_bags']} bags)"
            credit_tree.insert("", "end", values=(desc, f"{item_total_price:.2f}"))
            total_calculated_item_value += item_total_price
            total_quintals += item_total_quintals
            total_bags += item["num_bags"]

        amali_charge_rate = gp_data["amali_charge_per_quintal"]
        bag_charge_rate = gp_data["bag_charge_per_bag"]

        total_amali_charges = total_quintals * amali_charge_rate
        if total_amali_charges > 0:
            credit_tree.insert("", "end", values=("Amali Charges", f"{total_amali_charges:.2f}"))

        total_bag_charges_val = total_bags * bag_charge_rate
        if total_bag_charges_val > 0:
            credit_tree.insert("", "end", values=("Bag Charges", f"{total_bag_charges_val:.2f}"))

        credit_total_val = total_calculated_item_value + total_amali_charges + total_bag_charges_val

        # Verify with stored grand_total (should be very close, allowing for float precision)
        if abs(credit_total_val - gp_data['grand_total']) > 0.01 :
             credit_tree.insert("", "end", values=("DISCREPANCY IN CALC vs STORED TOTAL", ""))

        credit_total_label = ttk.Label(credit_outer_frame, text=f"GRAND TOTAL (Credit): ₹{gp_data['grand_total']:.2f}", font=('Arial', 10, 'bold'))
        credit_total_label.pack(side="bottom", pady=5, anchor="e")


        # --- Populate Debit Side ---
        debit_tree = ttk.Treeview(debit_outer_frame, columns=("lot", "qty", "price_qtl", "amount"), show="headings", height=8)
        debit_tree.heading("lot", text="Lot Name")
        debit_tree.heading("qty", text="Qty (Qtls)")
        debit_tree.heading("price_qtl", text="Price/Qtl (₹)")
        debit_tree.heading("amount", text="Amount (Dr.) ₹")

        debit_tree.column("lot", width=120)
        debit_tree.column("qty", width=80, anchor="e")
        debit_tree.column("price_qtl", width=100, anchor="e")
        debit_tree.column("amount", width=100, anchor="e")
        debit_tree.pack(fill="both", expand=True)

        cursor.execute("""
            SELECT lot_name, quantity_quintals, price_per_quintal, debit_amount
            FROM Transactions
            WHERE gate_pass_id = ? AND debit_amount > 0 AND description LIKE 'Sale of goods%'
        """, (gate_pass_id,))
        debit_transactions = cursor.fetchall()

        total_debit_amount = 0.0
        for trans in debit_transactions:
            debit_tree.insert("", "end", values=(
                trans["lot_name"],
                f"{trans['quantity_quintals']:.2f}",
                f"{trans['price_per_quintal']:.2f}",
                f"{trans['debit_amount']:.2f}"
            ))
            total_debit_amount += trans["debit_amount"]

        debit_total_label = ttk.Label(debit_outer_frame, text=f"TOTAL (Debit/COGS): ₹{total_debit_amount:.2f}", font=('Arial', 10, 'bold'))
        debit_total_label.pack(side="bottom", pady=5, anchor="e")


        # Final check: Grand Total (Credit) should match Total (Debit/COGS)
        # In this model, COGS is based on item sale price, so they should match.
        # If COGS were based on actual cost, they would differ.
        if abs(gp_data['grand_total'] - total_debit_amount) > 0.01:
             # This might indicate an issue in how transactions were recorded or interpreted
             mismatch_label = ttk.Label(main_display_frame, text="Warning: Credit Total and Debit Total (COGS) do not match significantly!", foreground="red")
             mismatch_label.pack(pady=5)


    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error fetching summary: {e}", parent=parent_window)
        return False # Indicate failure
    finally:
        if conn:
            conn.close()
    return True # Indicate success


def setup_transaction_summary_ui(parent_window):
    parent_window.title("Transaction Summary - Dr/Cr Paper")
    parent_window.geometry("800x650")

    top_controls_frame = ttk.Frame(parent_window, padding=10)
    top_controls_frame.pack(fill="x")

    selection_frame = ttk.Frame(top_controls_frame)
    selection_frame.pack(side="left", fill="x", expand=True)

    ttk.Label(selection_frame, text="Enter Gate Pass ID:").pack(side="left", padx=5)
    gp_id_entry = ttk.Entry(selection_frame, width=10)
    gp_id_entry.pack(side="left", padx=5)

    main_display_frame = ttk.Frame(parent_window, padding=10)
    main_display_frame.pack(expand=True, fill="both")

    current_gate_pass_id_for_print = {"value": None}

    # Modified on_view_summary_clicked to accept and pass db_path
    def on_view_summary_clicked(current_db_path=db_path): # Capture db_path from setup_ui
        print_pdf_button.state(["disabled"])
        current_gate_pass_id_for_print["value"] = None

        summary_loaded_successfully = fetch_and_display_summary(gp_id_entry, main_display_frame, parent_window, current_db_path) # Pass db_path

        if summary_loaded_successfully:
            try:
                current_gate_pass_id_for_print["value"] = int(gp_id_entry.get())
                print_pdf_button.state(["!disabled"])
            except ValueError:
                current_gate_pass_id_for_print["value"] = None

    # Pass db_path to the command
    view_button = ttk.Button(selection_frame, text="View Summary", command=lambda: on_view_summary_clicked(db_path))
    view_button.pack(side="left", padx=10)

    # Modified handle_print_transaction_summary_pdf_local to accept and pass db_path
    def handle_print_transaction_summary_pdf_local(current_db_path=db_path): # Capture db_path
        gp_id = current_gate_pass_id_for_print.get("value")
        if gp_id is None:
            messagebox.showwarning("Print Error", "No summary loaded or Gate Pass ID is invalid.", parent=parent_window)
            return

        default_filename = f"TransactionSummary_{gp_id}.pdf"
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports") # Relative to this UI file
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)

        filepath = filedialog.asksaveasfilename(
            parent=parent_window,
            title="Save Transaction Summary PDF",
            initialdir=reports_dir, # Suggests saving in rice_trading_app/reports/
            initialfile=default_filename,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filepath:
            # Pass db_path to the PDF generation function
            success, message = generate_transaction_summary_pdf(gp_id, filepath, current_db_path)
            if success:
                messagebox.showinfo("PDF Saved", message, parent=parent_window)
            else:
                messagebox.showerror("PDF Error", message, parent=parent_window)

    # Pass db_path to the command
    print_pdf_button = ttk.Button(top_controls_frame, text="Print to PDF",
                                  command=lambda: handle_print_transaction_summary_pdf_local(db_path))
    print_pdf_button.pack(side="right", padx=10)
    print_pdf_button.state(["disabled"])

    ttk.Label(main_display_frame, text="Enter a Gate Pass ID and click 'View Summary'.").pack(pady=20)


if __name__ == "__main__":
    STANDALONE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
    try:
        from ..database.database_setup import create_tables
        db_dir = os.path.dirname(STANDALONE_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        create_tables(STANDALONE_DB_PATH)
        print(f"Standalone TxSummaryUI: Ensured database exists at {STANDALONE_DB_PATH}")
    except ImportError:
        print("Standalone TxSummaryUI: Could not import create_tables. Assuming DB exists.")
    except Exception as e:
        print(f"Standalone TxSummaryUI: Error setting up DB: {e}")

    root = tk.Tk()
    # Pass the db_path to setup_transaction_summary_ui
    setup_transaction_summary_ui(root, STANDALONE_DB_PATH)
    root.mainloop()
