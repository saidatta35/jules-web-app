import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import os # For standalone __main__ path

# DATABASE_PATH = "../database/rice_trader.db" # No longer module-level constant

def get_db_connection(db_path=None):
    """Establishes a connection to the SQLite database."""
    if not db_path:
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            # from ..database.database_setup import create_tables # Consider for full standalone
            # create_tables(db_path)
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Good practice if you expect dict-like rows
        return conn
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not connect to database: {e} (Path: {db_path})")
        return None

class OrderDetailFrame(ttk.Frame):
    def __init__(self, parent, remove_callback, db_path_for_recalc_ref): # Pass db_path for recalc
        super().__init__(parent)
        self.parent = parent
        self.remove_callback = remove_callback
        self.db_path = db_path_for_recalc_ref # Store for potential use if needed by recalc, though not directly used now

        self.create_widgets()
        self.update_calculated_fields() # Initial calculation

    def create_widgets(self):
        ttk.Label(self, text="Lot Name:").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        self.lot_name_entry = ttk.Entry(self, width=15)
        self.lot_name_entry.grid(row=0, column=1, padx=2, pady=2)

        ttk.Label(self, text="Brand:").grid(row=0, column=2, padx=2, pady=2, sticky="w")
        self.brand_entry = ttk.Entry(self, width=15)
        self.brand_entry.grid(row=0, column=3, padx=2, pady=2)

        ttk.Label(self, text="Num Bags:").grid(row=1, column=0, padx=2, pady=2, sticky="w")
        self.num_bags_var = tk.StringVar()
        self.num_bags_var.trace_add("write", self.trigger_recalculation)
        self.num_bags_entry = ttk.Entry(self, width=10, textvariable=self.num_bags_var)
        self.num_bags_entry.grid(row=1, column=1, padx=2, pady=2)

        ttk.Label(self, text="Wt/Bag (kg):").grid(row=1, column=2, padx=2, pady=2, sticky="w")
        self.weight_per_bag_var = tk.StringVar()
        self.weight_per_bag_var.trace_add("write", self.trigger_recalculation)
        self.weight_per_bag_entry = ttk.Entry(self, width=10, textvariable=self.weight_per_bag_var)
        self.weight_per_bag_entry.grid(row=1, column=3, padx=2, pady=2)

        ttk.Label(self, text="Price/Qtl:").grid(row=1, column=4, padx=2, pady=2, sticky="w")
        self.price_per_quintal_var = tk.StringVar()
        self.price_per_quintal_var.trace_add("write", self.trigger_recalculation)
        self.price_per_quintal_entry = ttk.Entry(self, width=10, textvariable=self.price_per_quintal_var)
        self.price_per_quintal_entry.grid(row=1, column=5, padx=2, pady=2)

        self.total_weight_label_text = tk.StringVar(value="Total Wt: 0.00 Qtl")
        ttk.Label(self, textvariable=self.total_weight_label_text).grid(row=0, column=4, padx=5, pady=2, sticky="w")

        self.item_total_price_label_text = tk.StringVar(value="Item Total: ₹0.00")
        ttk.Label(self, textvariable=self.item_total_price_label_text).grid(row=0, column=5, padx=5, pady=2, sticky="w")

        remove_button = ttk.Button(self, text="Remove", command=self._remove_self)
        remove_button.grid(row=0, column=6, rowspan=2, padx=5, pady=2, sticky="e")

        # Separator for visual distinction
        ttk.Separator(self, orient='horizontal').grid(row=2, column=0, columnspan=7, sticky='ew', pady=5)


    def trigger_recalculation(self, *args):
        self.update_calculated_fields()

    def update_calculated_fields(self):
        try:
            num_bags = int(self.num_bags_var.get() or 0)
            weight_per_bag_kg = float(self.weight_per_bag_var.get() or 0)
            price_per_quintal = float(self.price_per_quintal_var.get() or 0)

            if num_bags < 0: num_bags = 0
            if weight_per_bag_kg < 0: weight_per_bag_kg = 0
            if price_per_quintal < 0: price_per_quintal = 0

            self.current_num_bags = num_bags # Store for parent access
            self.current_total_weight_quintals = (num_bags * weight_per_bag_kg) / 100.0
            self.current_item_total_price = self.current_total_weight_quintals * price_per_quintal

            self.total_weight_label_text.set(f"Total Wt: {self.current_total_weight_quintals:.2f} Qtl")
            self.item_total_price_label_text.set(f"Item Total: ₹{self.current_item_total_price:.2f}")
        except ValueError:
            self.current_num_bags = 0
            self.current_total_weight_quintals = 0.0
            self.current_item_total_price = 0.0
            self.total_weight_label_text.set("Total Wt: -- Qtl")
            self.item_total_price_label_text.set("Item Total: ₹--")

        # Propagate update to parent for grand total recalculation
        # The parent of OrderDetailFrame is scrollable_frame.
        # scrollable_frame.master is items_canvas.
        # items_canvas.master is order_details_frame.
        # order_details_frame.master is main_frame.
        # main_frame has recalculate_and_display_totals
        if hasattr(self.parent.master.master.master, 'recalculate_and_display_totals'):
             # This call is to the main_frame's method; it does not directly need db_path from here
             self.parent.master.master.master.recalculate_and_display_totals()


    def get_details(self): # db_path not directly needed here, validation is UI/logic based
        try:
            lot_name = self.lot_name_entry.get()
            if not lot_name:
                # messagebox.showerror("Item Error", "Lot Name in an item cannot be empty.")
                return None # Lot name is mandatory

            num_bags = int(self.num_bags_var.get() or 0)
            weight_per_bag_kg = float(self.weight_per_bag_var.get() or 0)
            price_per_quintal = float(self.price_per_quintal_var.get() or 0)

            # Validation for positive values is better handled during save_gate_pass
            # if num_bags <= 0 or weight_per_bag_kg <=0 or price_per_quintal < 0: # price can be 0
            #     pass

            return {
                "lot_name": lot_name,
                "brand": self.brand_entry.get(),
                "num_bags": num_bags,
                "weight_per_bag_kg": weight_per_bag_kg,
                "price_per_quintal": price_per_quintal,
                "total_weight_quintals": self.current_total_weight_quintals,
                "item_total_price": self.current_item_total_price
            }
        except ValueError:
            # messagebox.showerror("Item Error", "Invalid numeric input in one of the items.")
            return None # Indicates invalid data in this frame

    def _remove_self(self):
        self.remove_callback(self)

    def clear_fields(self):
        self.lot_name_entry.delete(0, tk.END)
        self.brand_entry.delete(0, tk.END)
        self.num_bags_var.set("0") # Triggers recalculation
        self.weight_per_bag_var.set("0") # Triggers recalculation
        self.price_per_quintal_var.set("0") # Triggers recalculation
        # self.update_calculated_fields() # Explicit call if var tracing is not enough for some reason


def setup_gate_pass_ui(parent_window, db_path): # Added db_path
    parent_window.title("Create Gate Pass")
    parent_window.columnconfigure(0, weight=1)
    parent_window.rowconfigure(0, weight=1)

    main_frame = ttk.Frame(parent_window, padding=(10,10))
    main_frame.db_path = db_path # Store db_path on main_frame for access by save_gate_pass etc.
    main_frame.grid(row=0, column=0, sticky="nsew")
    main_frame.columnconfigure(0, weight=1)

    # --- General Information Frame ---
    info_frame = ttk.LabelFrame(main_frame, text="General Information", padding=(10, 5))
    info_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew", columnspan=2) # Use grid
    info_frame.columnconfigure(1, weight=1) # Allow party name/address to expand
    info_frame.columnconfigure(3, weight=1) # Allow vehicle/broker to expand


    ttk.Label(info_frame, text="Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    main_frame.date_entry = ttk.Entry(info_frame, width=20)
    main_frame.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
    main_frame.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    ttk.Label(info_frame, text="Party Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    main_frame.party_name_entry = ttk.Entry(info_frame, width=40)
    main_frame.party_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    ttk.Label(info_frame, text="Address:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    main_frame.address_entry = ttk.Entry(info_frame, width=40)
    main_frame.address_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

    ttk.Label(info_frame, text="Vehicle No:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
    main_frame.vehicle_num_entry = ttk.Entry(info_frame, width=20)
    main_frame.vehicle_num_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    ttk.Label(info_frame, text="Broker Name:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
    main_frame.broker_name_entry = ttk.Entry(info_frame, width=20)
    main_frame.broker_name_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

    # --- Order Details Section ---
    order_details_frame = ttk.LabelFrame(main_frame, text="Order Items", padding=(10, 5))
    order_details_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew", columnspan=2) # Use grid
    main_frame.rowconfigure(1, weight=1) # Allow order_details_frame to expand vertically
    order_details_frame.columnconfigure(0, weight=1) # Allow canvas to expand
    order_details_frame.rowconfigure(0, weight=1) # Allow canvas to expand

    items_canvas = tk.Canvas(order_details_frame)
    items_canvas.grid(row=0, column=0, sticky="nsew")

    scrollbar = ttk.Scrollbar(order_details_frame, orient="vertical", command=items_canvas.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    items_canvas.configure(yscrollcommand=scrollbar.set)

    scrollable_frame = ttk.Frame(items_canvas)
    items_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="scrollable_frame")
    scrollable_frame.columnconfigure(0, weight=1) # Ensure item frames use full width

    def on_frame_configure(event):
        items_canvas.configure(scrollregion=items_canvas.bbox("all"))
        items_canvas.itemconfig("scrollable_frame", width=event.width) # Adjust width of scrollable_frame to canvas width


    scrollable_frame.bind("<Configure>", on_frame_configure)
    # Ensure the canvas width is passed to the scrollable_frame so it can adjust its children
    items_canvas.bind("<Configure>", lambda e: items_canvas.itemconfig('scrollable_frame', width=e.width))


    main_frame.order_item_frames = []

    def add_new_item_ui():
        # Pass db_path to OrderDetailFrame if it needs it for some internal logic (e.g. fetching lot details)
        # Currently, it's passed as db_path_for_recalc_ref but not used directly in recalc by OrderDetailFrame itself
        item_frame = OrderDetailFrame(scrollable_frame, remove_item_ui, main_frame.db_path)
        item_frame.grid(sticky='ew', pady=2)
        main_frame.order_item_frames.append(item_frame)
        main_frame.recalculate_and_display_totals()
        # Scroll to bottom
        items_canvas.update_idletasks()
        items_canvas.yview_moveto(1.0)


    def remove_item_ui(item_frame_to_remove):
        if item_frame_to_remove in main_frame.order_item_frames:
            item_frame_to_remove.destroy()
            main_frame.order_item_frames.remove(item_frame_to_remove)
            main_frame.recalculate_and_display_totals()
            # Update scrollregion after item removal
            scrollable_frame.update_idletasks()
            items_canvas.configure(scrollregion=items_canvas.bbox("all"))


    add_item_button = ttk.Button(order_details_frame, text="Add Item", command=add_new_item_ui)
    add_item_button.grid(row=1, column=0, pady=5, sticky="ew")

    # --- Charges Input Frame ---
    charges_frame = ttk.LabelFrame(main_frame, text="Charges", padding=(10,5))
    charges_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2) # Use grid

    ttk.Label(charges_frame, text="Amali Charge/Qtl:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
    main_frame.amali_charge_var = tk.StringVar(value="0.0")
    main_frame.amali_charge_var.trace_add("write", lambda *args: main_frame.recalculate_and_display_totals())
    amali_charge_entry = ttk.Entry(charges_frame, width=10, textvariable=main_frame.amali_charge_var)
    amali_charge_entry.grid(row=0, column=1, padx=5, pady=2)

    ttk.Label(charges_frame, text="Bag Charge/Bag:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
    main_frame.bag_charge_var = tk.StringVar(value="0.0")
    main_frame.bag_charge_var.trace_add("write", lambda *args: main_frame.recalculate_and_display_totals())
    bag_charge_entry = ttk.Entry(charges_frame, width=10, textvariable=main_frame.bag_charge_var)
    bag_charge_entry.grid(row=0, column=3, padx=5, pady=2)

    # --- Totals Display Frame ---
    totals_display_frame = ttk.LabelFrame(main_frame, text="Summary", padding=(10,5))
    totals_display_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew", columnspan=2) # Use grid

    main_frame.total_amali_var = tk.StringVar(value="Total Amali: ₹0.00")
    ttk.Label(totals_display_frame, textvariable=main_frame.total_amali_var).grid(row=0, column=0, padx=10, pady=2, sticky="w")

    main_frame.total_bag_var = tk.StringVar(value="Total Bags Charge: ₹0.00")
    ttk.Label(totals_display_frame, textvariable=main_frame.total_bag_var).grid(row=1, column=0, padx=10, pady=2, sticky="w")

    main_frame.grand_total_var = tk.StringVar(value="Grand Total: ₹0.00")
    ttk.Label(totals_display_frame, textvariable=main_frame.grand_total_var, font=("Arial", 12, "bold")).grid(row=0, column=1, rowspan=2, padx=20, pady=2, sticky="e")
    totals_display_frame.columnconfigure(1, weight=1) # Push grand total to the right

    def recalculate_and_display_totals_impl():
        total_item_price_sum = 0.0
        total_quintals_all_items = 0.0
        total_bags_all_items = 0

        for item_frame in main_frame.order_item_frames:
            # item_details = item_frame.get_details() # This can show error if data is bad during typing
            # Instead, use the stored current values from OrderDetailFrame
            total_item_price_sum += item_frame.current_item_total_price
            total_quintals_all_items += item_frame.current_total_weight_quintals
            total_bags_all_items += item_frame.current_num_bags

        try:
            amali_charge_per_quintal = float(main_frame.amali_charge_var.get() or 0)
            if amali_charge_per_quintal < 0: amali_charge_per_quintal = 0
        except ValueError:
            amali_charge_per_quintal = 0.0

        try:
            bag_charge_per_bag = float(main_frame.bag_charge_var.get() or 0)
            if bag_charge_per_bag < 0: bag_charge_per_bag = 0
        except ValueError:
            bag_charge_per_bag = 0.0

        total_amali_charges = total_quintals_all_items * amali_charge_per_quintal
        total_bag_charges = total_bags_all_items * bag_charge_per_bag
        grand_total = total_item_price_sum + total_amali_charges + total_bag_charges

        main_frame.total_amali_var.set(f"Total Amali: ₹{total_amali_charges:.2f}")
        main_frame.total_bag_var.set(f"Total Bags Charge: ₹{total_bag_charges:.2f}")
        main_frame.grand_total_var.set(f"Grand Total: ₹{grand_total:.2f}")

        # Store calculated values on main_frame for save_gate_pass to access
        main_frame.calculated_total_item_price_sum = total_item_price_sum
        main_frame.calculated_total_amali_charges = total_amali_charges
        main_frame.calculated_total_bag_charges = total_bag_charges
        main_frame.calculated_grand_total = grand_total


    main_frame.recalculate_and_display_totals = recalculate_and_display_totals_impl

    # --- Save Button ---
    # save_gate_pass needs db_path, which is stored on main_frame (mf)
    save_button = ttk.Button(main_frame, text="Save Gate Pass", command=lambda: save_gate_pass(main_frame))
    save_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")


    # Add one initial item & initial calculation
    add_new_item_ui()

def clear_gate_pass_form(mf): # mf is main_frame
    mf.date_entry.delete(0, tk.END)
    mf.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
    mf.party_name_entry.delete(0, tk.END)
    mf.address_entry.delete(0, tk.END)
    mf.vehicle_num_entry.delete(0, tk.END)
    mf.broker_name_entry.delete(0, tk.END)

    mf.amali_charge_var.set("0.0")
    mf.bag_charge_var.set("0.0")

    # Remove all existing item frames except one, then clear it
    for i in range(len(mf.order_item_frames) -1, 0, -1): # Iterate backwards
        mf.order_item_frames[i].destroy()
        mf.order_item_frames.pop(i)

    if mf.order_item_frames: # Clear the first (and now only) item frame
        mf.order_item_frames[0].clear_fields()
    else: # If all were removed somehow, add a fresh one
        # This part of the logic is a bit tricky; the original add_new_item_ui needs to be callable
        # For simplicity, we assume setup_gate_pass_ui's add_new_item_ui is what we need
        # However, direct call might be complex. Let's refine add_new_item_ui call if needed.
        # A simpler way: ensure there's always one frame, just clear it.
        # The original add_new_item_ui is defined within setup_gate_pass_ui, so not directly callable here.
        # We'll rely on the fact that it should leave one frame, which is then cleared.
        # If no items, the add_new_item_ui in setup_gate_pass_ui should be called to add one.
        # This is handled by the initial add_new_item_ui if list becomes empty.
        # For now, just clearing the first one if it exists.
    # If list is empty (e.g. user removes the last one), add_new_item_ui (bound to main_frame) should be called.
    # However, add_new_item_ui is not directly available here.
    # A robust clear would ensure one item frame exists.
    # For now, if order_item_frames is empty, the form is clear of items.
    # The next add_new_item_ui call (via button) would repopulate.
    if not mf.order_item_frames: # If user somehow removed all items (not default behavior)
        # We need a way to call add_new_item_ui here.
        # This is tricky because add_new_item_ui is nested.
        # A simpler solution: the "Add Item" button is always there.
        # Or, ensure clear_gate_pass_form is always followed by adding one item if none exist.
        # For now, we assume the user will use "Add Item" if the list is empty.
        pass # Or explicitly call the add_new_item_ui if it were available globally or on mf


    mf.recalculate_and_display_totals() # Reset totals display


def save_gate_pass(mf): # mf is main_frame, which should have db_path
    db_path = mf.db_path # Retrieve db_path from main_frame
    # 1. Gather Data
    date = mf.date_entry.get()
    party_name = mf.party_name_entry.get()
    address = mf.address_entry.get()
    vehicle_number = mf.vehicle_num_entry.get()
    broker_name = mf.broker_name_entry.get()

    try:
        amali_charge_rate = float(mf.amali_charge_var.get() or 0)
        if amali_charge_rate < 0: amali_charge_rate = 0
    except ValueError:
        messagebox.showerror("Input Error", "Invalid Amali Charge per Quintal.")
        return

    try:
        bag_charge_rate = float(mf.bag_charge_var.get() or 0)
        if bag_charge_rate < 0: bag_charge_rate = 0
    except ValueError:
        messagebox.showerror("Input Error", "Invalid Bag Charge per Bag.")
        return

    order_items_data = []
    for item_frame in mf.order_item_frames:
        details = item_frame.get_details()
        if details: # Ensure item_frame has valid data structure
            order_items_data.append(details)
        else: # If get_details returned None due to internal validation (e.g. empty lot_name)
            messagebox.showerror("Input Error", "Invalid data in one or more order items. Lot name is mandatory, and numeric fields must be valid numbers.")
            return


    # 2. Input Validation
    if not date: # Date is pre-filled, but good to check
        messagebox.showerror("Input Error", "Date cannot be empty.")
        return
    if not party_name:
        messagebox.showerror("Input Error", "Party Name cannot be empty.")
        return
    if not order_items_data:
        messagebox.showerror("Input Error", "At least one order item must be added.")
        return

    for item in order_items_data:
        if not item["lot_name"]: # Already checked by get_details, but as a safeguard
            messagebox.showerror("Input Error", "Lot Name in an order item cannot be empty.")
            return
        # Check for positive values for quantities and prices if that's a strict rule at save time
        if item["num_bags"] <= 0 or item["weight_per_bag_kg"] <= 0 or item["price_per_quintal"] < 0:
             messagebox.showerror("Input Error", f"Item '{item['lot_name']}': Number of bags, weight per bag, and price must be positive values (price can be zero).")
             return


    # Retrieve calculated totals from where they were stored by recalculate_and_display_totals
    grand_total_to_save = mf.calculated_grand_total
    total_amali_to_save = mf.calculated_total_amali_charges
    total_bag_to_save = mf.calculated_total_bag_charges
    total_item_price_sum_to_save = mf.calculated_total_item_price_sum


    # 3. Database Operations
    conn = get_db_connection(db_path) # Pass db_path
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION;')

        # Insert into GatePasses
        cursor.execute("""
            INSERT INTO GatePasses (date, party_name, address, vehicle_number, broker_name,
                                   amali_charge_per_quintal, bag_charge_per_bag, grand_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, party_name, address, vehicle_number, broker_name,
              amali_charge_rate, bag_charge_rate, grand_total_to_save))
        gate_pass_id = cursor.lastrowid
        if not gate_pass_id:
            raise sqlite3.Error("Failed to get gate_pass_id (lastrowid).")


        for item in order_items_data:
            # Insert into GatePassOrderDetails
            cursor.execute("""
                INSERT INTO GatePassOrderDetails (gate_pass_id, lot_name, brand, num_bags,
                                                 weight_per_bag_kg, price_per_quintal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (gate_pass_id, item["lot_name"], item["brand"], item["num_bags"],
                  item["weight_per_bag_kg"], item["price_per_quintal"]))

            # Stock Update
            cursor.execute("SELECT quantity_quintals FROM Stock WHERE lot_name = ?", (item["lot_name"],))
            stock_row = cursor.fetchone()
            current_quantity = 0.0
            if stock_row:
                current_quantity = stock_row[0]
            else:
                # Optionally, handle case where lot_name does not exist in stock yet.
                # For now, this means current_quantity is 0, and it will go negative.
                # Or, one could insert the lot with 0 quantity first if strict stock existence is required.
                 messagebox.showwarning("Stock Warning", f"Lot '{item['lot_name']}' does not exist in stock. It will be created with a negative quantity.")
                 # Insert the stock item if it doesn't exist to avoid FK issues if Transactions referred Stock.ID
                 # cursor.execute("INSERT OR IGNORE INTO Stock (lot_name, quantity_quintals) VALUES (?, 0)", (item["lot_name"],))


            new_quantity = current_quantity - item["total_weight_quintals"]
            if new_quantity < 0:
                messagebox.showwarning("Stock Warning", f"Stock for lot '{item['lot_name']}' will go to {new_quantity:.2f} quintals.")

            cursor.execute("""
                UPDATE Stock SET quantity_quintals = ? WHERE lot_name = ?
            """, (new_quantity, item["lot_name"]))

            if cursor.rowcount == 0: # If lot_name didn't exist, the update does nothing. Insert it.
                 cursor.execute("INSERT INTO Stock (lot_name, quantity_quintals) VALUES (?, ?)",
                                (item["lot_name"], new_quantity))


            # Insert into Transactions (Debit - Cost of Goods Sold for this item)
            item_cogs = item["total_weight_quintals"] * item["price_per_quintal"] # This is item_total_price
            cursor.execute("""
                INSERT INTO Transactions (gate_pass_id, date, description, lot_name,
                                          quantity_quintals, price_per_quintal, debit_amount, credit_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (gate_pass_id, date, f"Sale of goods - Lot: {item['lot_name']}", item["lot_name"],
                  item["total_weight_quintals"], item["price_per_quintal"], item_cogs))

        # Insert into Transactions (Credit - Sales Revenue for all items)
        if total_item_price_sum_to_save > 0 : # Only if there's actual revenue from items
            cursor.execute("""
                INSERT INTO Transactions (gate_pass_id, date, description, debit_amount, credit_amount)
                VALUES (?, ?, ?, 0, ?)
            """, (gate_pass_id, date, "Sales Revenue - Items", total_item_price_sum_to_save))

        # Insert into Transactions (Credit - Amali Charges Collected)
        if total_amali_to_save > 0:
            cursor.execute("""
                INSERT INTO Transactions (gate_pass_id, date, description, debit_amount, credit_amount)
                VALUES (?, ?, ?, 0, ?)
            """, (gate_pass_id, date, "Amali Charges Collected", total_amali_to_save))

        # Insert into Transactions (Credit - Bag Charges Collected)
        if total_bag_to_save > 0:
            cursor.execute("""
                INSERT INTO Transactions (gate_pass_id, date, description, debit_amount, credit_amount)
                VALUES (?, ?, ?, 0, ?)
            """, (gate_pass_id, date, "Bag Charges Collected", total_bag_to_save))

        conn.commit()
        messagebox.showinfo("Success", "Gate Pass saved successfully!")
        clear_gate_pass_form(mf) # Clear form for next entry

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        messagebox.showerror("Database Error", f"Failed to save Gate Pass: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Standalone execution
    STANDALONE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")

    try:
        from ..database.database_setup import create_tables
        db_dir = os.path.dirname(STANDALONE_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        create_tables(STANDALONE_DB_PATH)
        print(f"Standalone GatePassUI: Ensured database exists at {STANDALONE_DB_PATH}")
    except ImportError:
        print("Standalone GatePassUI: Could not import create_tables. Assuming DB exists.")
    except Exception as e:
        print(f"Standalone GatePassUI: Error setting up DB: {e}")

    root = tk.Tk()
    root.geometry("850x700")
    setup_gate_pass_ui(root, STANDALONE_DB_PATH) # Pass standalone DB path
    root.mainloop()
