import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from logic.pdf_generator import generate_gate_pass_pdf # Corrected import path
import os

# DATABASE_PATH = "../database/rice_trader.db" # No longer module-level constant

def get_db_connection(db_path=None): # Added db_path parameter
    """Establishes a connection to the SQLite database."""
    if not db_path:
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            # from ..database.database_setup import create_tables
            # create_tables(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not connect to database: {e} (Path: {db_path})")
        return None

def display_gate_pass_details(gate_pass_id, parent_window, db_path): # Added db_path
    """Displays all details of a selected gate pass in a new Toplevel window."""
    if not gate_pass_id:
        messagebox.showwarning("Selection Error", "No gate pass selected to view details.", parent=parent_window)
        return

    details_window = tk.Toplevel(parent_window)
    details_window.title(f"Gate Pass Details - ID: {gate_pass_id}")
    details_window.geometry("700x550")

    notebook = ttk.Notebook(details_window)
    notebook.pack(expand=True, fill='both', padx=10, pady=10)

    # --- General Info Tab ---
    general_tab = ttk.Frame(notebook, padding=10)
    notebook.add(general_tab, text='General Information & Charges')

    conn = get_db_connection(db_path) # Pass db_path
    if not conn: return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM GatePasses WHERE gate_pass_id = ?", (gate_pass_id,))
        gp_data = cursor.fetchone()

        if not gp_data:
        messagebox.showerror("Error", f"Could not find Gate Pass with ID {gate_pass_id}", parent=details_window)
            details_window.destroy()
            return

        fields_to_display = [
            ("Gate Pass ID:", gp_data["gate_pass_id"]),
            ("Date:", gp_data["date"]),
            ("Party Name:", gp_data["party_name"]),
            ("Address:", gp_data["address"]),
            ("Vehicle Number:", gp_data["vehicle_number"]),
            ("Broker Name:", gp_data["broker_name"]),
            ("Amali Charge/Qtl:", f"₹{gp_data['amali_charge_per_quintal']:.2f}"),
            ("Bag Charge/Bag:", f"₹{gp_data['bag_charge_per_bag']:.2f}"),
            ("Grand Total:", f"₹{gp_data['grand_total']:.2f} (as saved)"),
        ]

        for i, (label_text, value_text) in enumerate(fields_to_display):
            ttk.Label(general_tab, text=label_text, font=('Arial', 10, 'bold')).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            ttk.Label(general_tab, text=value_text if value_text else "N/A").grid(row=i, column=1, sticky="w", padx=5, pady=3)

        ttk.Separator(general_tab, orient='horizontal').grid(row=len(fields_to_display), column=0, columnspan=2, sticky='ew', pady=10)

        # --- Order Details Tab ---
        orders_tab = ttk.Frame(notebook, padding=10)
        notebook.add(orders_tab, text='Order Items')

        order_tree = ttk.Treeview(orders_tab, columns=("lot", "brand", "bags", "wt_bag", "price_qtl", "total_wt", "item_total"), show="headings")
        order_tree.heading("lot", text="Lot Name")
        order_tree.heading("brand", text="Brand")
        order_tree.heading("bags", text="Num Bags")
        order_tree.heading("wt_bag", text="Wt/Bag (kg)")
        order_tree.heading("price_qtl", text="Price/Qtl (₹)")
        order_tree.heading("total_wt", text="Total Wt (Qtl)")
        order_tree.heading("item_total", text="Item Total (₹)")

        cols_width = {"lot": 100, "brand": 100, "bags": 70, "wt_bag": 80, "price_qtl":100, "total_wt":100, "item_total":100}
        for col, width in cols_width.items():
            order_tree.column(col, width=width, anchor="center")

        order_tree.pack(expand=True, fill='both')

        cursor.execute("SELECT lot_name, brand, num_bags, weight_per_bag_kg, price_per_quintal FROM GatePassOrderDetails WHERE gate_pass_id = ?", (gate_pass_id,))
        order_items = cursor.fetchall()

        calculated_total_items_price = 0.0
        calculated_total_quintals = 0.0
        calculated_total_bags = 0

        for item in order_items:
            total_wt_qtl = (item["num_bags"] * item["weight_per_bag_kg"]) / 100.0
            item_total_val = total_wt_qtl * item["price_per_quintal"]
            order_tree.insert("", "end", values=(
                item["lot_name"], item["brand"], item["num_bags"],
                f"{item['weight_per_bag_kg']:.2f}", f"{item['price_per_quintal']:.2f}",
                f"{total_wt_qtl:.2f}", f"{item_total_val:.2f}"
            ))
            calculated_total_items_price += item_total_val
            calculated_total_quintals += total_wt_qtl
            calculated_total_bags += item["num_bags"]

        # Display calculated totals for charges based on items
        ttk.Separator(general_tab, orient='horizontal').grid(row=len(fields_to_display)+1, column=0, columnspan=2, sticky='ew', pady=10)
        ttk.Label(general_tab, text="Calculated from Items:", font=('Arial', 10, 'bold', 'italic')).grid(row=len(fields_to_display)+2, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        total_amali_charge_calc = calculated_total_quintals * gp_data["amali_charge_per_quintal"]
        total_bag_charge_calc = calculated_total_bags * gp_data["bag_charge_per_bag"]
        grand_total_calc = calculated_total_items_price + total_amali_charge_calc + total_bag_charge_calc

        calc_fields = [
            ("Total Item Value:", f"₹{calculated_total_items_price:.2f}"),
            ("Total Amali Charges:", f"₹{total_amali_charge_calc:.2f} ({calculated_total_quintals:.2f} Qtl * ₹{gp_data['amali_charge_per_quintal']:.2f}/Qtl)"),
            ("Total Bag Charges:", f"₹{total_bag_charge_calc:.2f} ({calculated_total_bags} bags * ₹{gp_data['bag_charge_per_bag']:.2f}/bag)"),
            ("Calculated Grand Total:", f"₹{grand_total_calc:.2f}"),
        ]

        current_row = len(fields_to_display) + 3
        for i, (label_text, value_text) in enumerate(calc_fields):
            ttk.Label(general_tab, text=label_text, font=('Arial', 10, 'italic')).grid(row=current_row+i, column=0, sticky="w", padx=10, pady=3)
            ttk.Label(general_tab, text=value_text).grid(row=current_row+i, column=1, sticky="w", padx=5, pady=3)

        # PDF Print Button
        def handle_print_gate_pass_pdf_local(current_gp_id):
            default_filename = f"GatePass_{current_gp_id}.pdf"
            # Default to 'reports' directory if it exists, else current dir
            reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports") # Assumes ui is one level down from app root
            if not os.path.exists(reports_dir):
                 os.makedirs(reports_dir, exist_ok=True) # Create if not exists

            filepath = filedialog.asksaveasfilename(
                parent=details_window,
                title="Save Gate Pass PDF",
                initialdir=reports_dir,
                initialfile=default_filename,
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            if filepath:
                # generate_gate_pass_pdf will need db_path
                success, message = generate_gate_pass_pdf(current_gp_id, filepath, db_path)
                if success:
                    messagebox.showinfo("PDF Saved", message, parent=details_window)
                else:
                    messagebox.showerror("PDF Error", message, parent=details_window)

        print_button = ttk.Button(details_window, text="Print to PDF",
                                  command=lambda: handle_print_gate_pass_pdf_local(gate_pass_id))
        print_button.pack(pady=10)


    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Error fetching details: {e}", parent=details_window)
        details_window.destroy()
    finally:
        if conn:
            conn.close()

    details_window.transient(parent_window)
    details_window.grab_set()
    parent_window.wait_window(details_window)


def load_gate_passes(tree, db_path, filters=None): # Added db_path
    """Loads gate passes into the Treeview, applying optional filters."""
    for item in tree.get_children():
        tree.delete(item)

    conn = get_db_connection(db_path) # Pass db_path
    if not conn: return

    query = "SELECT gate_pass_id, date, party_name, vehicle_number, broker_name, grand_total FROM GatePasses"
    params = []
    where_clauses = []

    if filters:
        if filters.get("party_name"):
            where_clauses.append("party_name LIKE ?")
            params.append(f"%{filters['party_name']}%")
        if filters.get("date"):
            where_clauses.append("date = ?")
            params.append(filters['date'])
        if filters.get("gate_pass_id"):
            where_clauses.append("gate_pass_id = ?")
            params.append(filters['gate_pass_id'])

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY date DESC, gate_pass_id DESC"

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            tree.insert("", "end", values=(row["gate_pass_id"], row["date"], row["party_name"],
                                           row["vehicle_number"] or "", row["broker_name"] or "", f"{row['grand_total']:.2f}"))
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to load gate passes: {e}")
    finally:
        if conn:
            conn.close()


def setup_view_gate_passes_ui(parent_window, db_path): # Added db_path
    parent_window.title("View Saved Gate Passes")
    parent_window.geometry("900x600")
    # Store db_path on parent_window or main_frame if needed by deeply nested functions
    # For now, pass it directly where needed.
    # parent_window.db_path = db_path

    main_frame = ttk.Frame(parent_window, padding=10)
    main_frame.pack(expand=True, fill='both')

    # --- Search/Filter Frame ---
    filter_frame = ttk.LabelFrame(main_frame, text="Search Filters", padding=10)
    filter_frame.pack(fill="x", padx=5, pady=5)

    ttk.Label(filter_frame, text="Party Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    party_filter_entry = ttk.Entry(filter_frame, width=20)
    party_filter_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(filter_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    date_filter_entry = ttk.Entry(filter_frame, width=15)
    date_filter_entry.grid(row=0, column=3, padx=5, pady=5)

    ttk.Label(filter_frame, text="Gate Pass ID:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
    id_filter_entry = ttk.Entry(filter_frame, width=10)
    id_filter_entry.grid(row=0, column=5, padx=5, pady=5)

    search_button = ttk.Button(filter_frame, text="Search", command=lambda: apply_filters(db_path)) # Pass db_path
    search_button.grid(row=0, column=6, padx=10, pady=5)

    clear_button = ttk.Button(filter_frame, text="Clear Filters", command=lambda: clear_all_filters(db_path)) # Pass db_path
    clear_button.grid(row=0, column=7, padx=5, pady=5)

    filter_frame.columnconfigure(1, weight=1)
    filter_frame.columnconfigure(3, weight=1)
    filter_frame.columnconfigure(5, weight=1)


    # --- Gate Pass List Display ---
    list_frame = ttk.LabelFrame(main_frame, text="Gate Passes", padding=10)
    list_frame.pack(expand=True, fill="both", padx=5, pady=5)

    columns = ("id", "date", "party", "vehicle", "broker", "total")
    gp_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
    gp_tree.heading("id", text="GP ID")
    gp_tree.heading("date", text="Date")
    gp_tree.heading("party", text="Party Name")
    gp_tree.heading("vehicle", text="Vehicle No.")
    gp_tree.heading("broker", text="Broker")
    gp_tree.heading("total", text="Grand Total (₹)")

    gp_tree.column("id", width=60, anchor="center")
    gp_tree.column("date", width=100, anchor="center")
    gp_tree.column("party", width=200)
    gp_tree.column("vehicle", width=100, anchor="center")
    gp_tree.column("broker", width=120)
    gp_tree.column("total", width=100, anchor="e")

    # Scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=gp_tree.yview)
    gp_tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    gp_tree.pack(expand=True, fill="both", side="left")

    def apply_filters(current_db_path): # Receive db_path
        filters = {
            "party_name": party_filter_entry.get(),
            "date": date_filter_entry.get(),
            "gate_pass_id": id_filter_entry.get()
        }
        filters = {k: v for k, v in filters.items() if v} # Remove empty filters
        load_gate_passes(gp_tree, current_db_path, filters)

    def clear_all_filters(current_db_path): # Receive db_path
        party_filter_entry.delete(0, tk.END)
        date_filter_entry.delete(0, tk.END)
        id_filter_entry.delete(0, tk.END)
        load_gate_passes(gp_tree, current_db_path)

    # --- View Details Button ---
    details_button = ttk.Button(main_frame, text="View Full Details", command=lambda: on_view_details(db_path)) # Pass db_path
    details_button.pack(pady=10)

    def on_view_details(current_db_path): # Receive db_path
        selected_item = gp_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select a gate pass from the list to view details.")
            return
        item_values = gp_tree.item(selected_item, "values")
        if item_values:
            gate_pass_id_to_view = item_values[0]
            display_gate_pass_details(gate_pass_id_to_view, parent_window, current_db_path) # Pass db_path

    # Double click to view details
    def on_double_click(event, current_db_path=db_path): # Pass db_path, default to the one from setup_ui
        item = gp_tree.identify('item', event.x, event.y)
        if item:
            gp_tree.selection_set(item)
            gp_tree.focus(item)
            on_view_details(current_db_path) # Pass db_path

    gp_tree.bind("<Double-1>", lambda event: on_double_click(event, db_path)) # Pass db_path to handler


    # Initial load
    load_gate_passes(gp_tree, db_path)


if __name__ == "__main__":
    STANDALONE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
    try:
        from ..database.database_setup import create_tables
        db_dir = os.path.dirname(STANDALONE_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        create_tables(STANDALONE_DB_PATH)
        print(f"Standalone ViewGatePassesUI: Ensured database exists at {STANDALONE_DB_PATH}")
    except ImportError:
        print("Standalone ViewGatePassesUI: Could not import create_tables. Assuming DB exists.")
    except Exception as e:
        print(f"Standalone ViewGatePassesUI: Error setting up DB: {e}")

    root = tk.Tk()
    setup_view_gate_passes_ui(root, STANDALONE_DB_PATH)
    root.mainloop()
