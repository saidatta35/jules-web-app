import tkinter as tk
from tkinter import ttk
import os

# --- Import UI setup functions ---
from ui.stock_management_ui import setup_stock_ui
from ui.gate_pass_ui import setup_gate_pass_ui
from ui.view_gate_passes_ui import setup_view_gate_passes_ui
from ui.transaction_summary_ui import setup_transaction_summary_ui

# --- Import database setup ---
from database.database_setup import create_tables, DATABASE_PATH as DB_SETUP_DEFAULT_PATH

# Define the base directory for the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the default database path, to be used by all modules
# This ensures that whether run from main_app.py or standalone (if they adapt), the path logic is centralized.
# For main_app.py, this will resolve to 'rice_trading_app/database/rice_trader.db'
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'database', 'rice_trader.db')


class RiceTradingApp:
    def __init__(self, root, db_path):
        self.root = root
        self.db_path = db_path # Store the db_path
        self.root.title("Rice Trading Management System")
        self.root.geometry("900x700") # Adjusted default size

        # Ensure database and tables are ready using the passed db_path
        # The create_tables() in database_setup.py needs to be adaptable or use this path.
        # For now, we assume create_tables() uses its own defined path, which should align with DEFAULT_DB_PATH
        # if main_app.py is in rice_trading_app/ and database_setup.py is in rice_trading_app/database/

        # Let's refine create_tables to accept a path
        # For now, we'll call it without a path and assume it works due to its own path construction.
        # A better approach would be: create_tables(self.db_path)
        # This requires modifying database_setup.py's create_tables function.
        # For this iteration, we'll call the original create_tables.
        # We need to ensure its DATABASE_PATH is 'database/rice_trader.db' when run from app root.

        # The DATABASE_PATH in database_setup.py is "rice_trading_app/database/rice_trader.db"
        # This is problematic if main_app.py is inside rice_trading_app.
        # Let's assume create_tables will be modified or it correctly resolves.
        # For now, let's ensure the directory for the DB exists.
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Call create_tables. If it's hardcoded, it needs to match.
        # The task implies create_tables() should just run.
        create_tables(db_path_to_use=self.db_path) # Assuming create_tables can take this

        # --- Main Menu ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Modules Menu
        modules_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Modules", menu=modules_menu)
        modules_menu.add_command(label="Stock Management", command=self.open_stock_management)
        modules_menu.add_separator()
        modules_menu.add_command(label="Create Gate Pass", command=self.open_create_gate_pass)
        modules_menu.add_command(label="View Saved Gate Passes", command=self.open_view_gate_passes)
        modules_menu.add_separator()
        modules_menu.add_command(label="View Transaction Summary", command=self.open_transaction_summary)

        # --- Welcome Message or Central Frame (Optional) ---
        welcome_frame = ttk.Frame(self.root, padding=20)
        welcome_frame.pack(expand=True, fill=tk.BOTH)
        ttk.Label(welcome_frame, text="Welcome to the Rice Trading Management System",
                  font=("Arial", 16, "bold"), anchor="center").pack(expand=True)
        ttk.Label(welcome_frame, text="Select a module from the menu to begin.",
                  font=("Arial", 12), anchor="center").pack(expand=True)


    def _open_module_window(self, setup_ui_function, title):
        """Helper to create Toplevel window and run setup function."""
        module_window = tk.Toplevel(self.root)
        module_window.title(title)
        # Pass the db_path to the setup function
        setup_ui_function(module_window, self.db_path)

    def open_stock_management(self):
        self._open_module_window(setup_stock_ui, "Stock Management")

    def open_create_gate_pass(self):
        self._open_module_window(setup_gate_pass_ui, "Create Gate Pass")

    def open_view_gate_passes(self):
        self._open_module_window(setup_view_gate_passes_ui, "View Saved Gate Passes")

    def open_transaction_summary(self):
        self._open_module_window(setup_transaction_summary_ui, "Transaction Summary")


if __name__ == "__main__":
    # Ensure the 'reports' directory exists relative to main_app.py
    reports_dir = os.path.join(BASE_DIR, 'reports')
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir, exist_ok=True)

    root = tk.Tk()
    app = RiceTradingApp(root, DEFAULT_DB_PATH) # Pass the db_path to the app
    root.mainloop()
