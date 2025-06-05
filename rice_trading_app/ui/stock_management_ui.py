import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os # For standalone __main__ path

# This will be set by main_app.py or by __main__ block here
# No longer a fixed constant at the module level for get_db_connection
# DATABASE_PATH = "../database/rice_trader.db"

def get_db_connection(db_path=None):
    """Establishes a connection to the SQLite database."""
    if not db_path:
        # Fallback for standalone execution or if path isn't passed (should not happen via main_app)
        # This path is relative to this ui file's location when run standalone.
        db_path = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")
        # Ensure the directory exists for standalone test
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            # Potentially call create_tables here if you want standalone to fully init
            # from ...database.database_setup import create_tables
            # create_tables(db_path)


    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Could not connect to database: {e} (Path: {db_path})")
        return None

def add_stock(lot_name_entry, quantity_entry, tree, db_path): # Added db_path
    """Adds a new stock item to the database."""
    lot_name = lot_name_entry.get()
    quantity_str = quantity_entry.get()

    if not lot_name:
        messagebox.showerror("Input Error", "Lot Name cannot be empty.")
        return

    try:
        quantity = float(quantity_str)
        if quantity <= 0:
            messagebox.showerror("Input Error", "Quantity must be a positive number.")
            return
    except ValueError:
        messagebox.showerror("Input Error", "Quantity must be a valid number.")
        return

    conn = get_db_connection(db_path) # Pass db_path
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Stock (lot_name, quantity_quintals) VALUES (?, ?)",
                           (lot_name, quantity))
            conn.commit()
            messagebox.showinfo("Success", "Stock added successfully.")
            lot_name_entry.delete(0, tk.END)
            quantity_entry.delete(0, tk.END)
            view_stock(tree, db_path) # Pass db_path
        except sqlite3.IntegrityError:
            messagebox.showerror("Database Error", f"Lot Name '{lot_name}' already exists.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add stock: {e}")
        finally:
            conn.close()

def view_stock(tree, db_path): # Added db_path
    """Populates the Treeview widget with stock data from the database."""
    for item in tree.get_children():
        tree.delete(item)

    conn = get_db_connection(db_path) # Pass db_path
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT stock_id, lot_name, quantity_quintals FROM Stock ORDER BY lot_name")
            rows = cursor.fetchall()
            for row in rows:
                tree.insert("", tk.END, values=row)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to retrieve stock: {e}")
        finally:
            conn.close()

def setup_stock_ui(parent_window, db_path): # Added db_path
    """Sets up the UI for stock management."""
    parent_window.title("Stock Management")
    parent_window.geometry("600x450")


    # Frame for adding stock
    add_frame = ttk.LabelFrame(parent_window, text="Add New Stock", padding=(10, 5))
    add_frame.pack(padx=10, pady=10, fill="x", expand=False)

    ttk.Label(add_frame, text="Lot Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    lot_name_entry = ttk.Entry(add_frame, width=30)
    lot_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    ttk.Label(add_frame, text="Quantity (Quintals):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    quantity_entry = ttk.Entry(add_frame, width=30)
    quantity_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    add_button = ttk.Button(add_frame, text="Add Stock",
                            command=lambda: add_stock(lot_name_entry, quantity_entry, stock_tree_view, db_path)) # Pass db_path
    add_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)

    # Frame for displaying stock
    display_frame = ttk.LabelFrame(parent_window, text="Current Stock", padding=(10, 5))
    display_frame.pack(padx=10, pady=10, fill="both", expand=True)

    columns = ("stock_id", "lot_name", "quantity_quintals")
    stock_tree_view = ttk.Treeview(display_frame, columns=columns, show="headings", height=10)

    stock_tree_view.heading("stock_id", text="Stock ID")
    stock_tree_view.heading("lot_name", text="Lot Name")
    stock_tree_view.heading("quantity_quintals", text="Quantity (Quintals)")

    stock_tree_view.column("stock_id", width=80, anchor="center")
    stock_tree_view.column("lot_name", width=200)
    stock_tree_view.column("quantity_quintals", width=150, anchor="e") # e for east (right align)

    stock_tree_view.pack(fill="both", expand=True)

    # Initial population of the tree
    view_stock(stock_tree_view, db_path) # Pass db_path

    # Add a refresh button (optional, but good for UX)
    refresh_button = ttk.Button(display_frame, text="Refresh Stock List",
                                command=lambda: view_stock(stock_tree_view, db_path)) # Pass db_path
    refresh_button.pack(pady=5)


if __name__ == "__main__":
    # Standalone execution: Use a relative path to where the DB should be
    # This assumes the script is in rice_trading_app/ui/
    # and the database is in rice_trading_app/database/
    STANDALONE_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "rice_trader.db")

    # Optional: Ensure DB and tables exist for standalone run
    # This requires importing create_tables from database_setup.py
    try:
        from ..database.database_setup import create_tables
        # Ensure the directory for the DB exists
        db_dir = os.path.dirname(STANDALONE_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        create_tables(STANDALONE_DB_PATH)
        print(f"Standalone: Ensured database exists at {STANDALONE_DB_PATH}")
    except ImportError:
        print("Standalone: Could not import create_tables. Assuming DB exists.")
    except Exception as e:
        print(f"Standalone: Error setting up DB: {e}")


    root = tk.Tk()
    # Pass the determined standalone DB path to the setup function
    setup_stock_ui(root, STANDALONE_DB_PATH)
    root.mainloop()
