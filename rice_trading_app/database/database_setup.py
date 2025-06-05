import sqlite3
import os

# This can be the default path if no path is provided to create_tables
# For consistency, this should ideally be relative to this file, or an absolute path.
# However, main_app.py will now define the primary path.
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "rice_trader.db") # Default if run standalone

def create_tables(db_path_to_use=None):
    """Connects to the database and creates the necessary tables.
    Uses db_path_to_use if provided, otherwise defaults to DATABASE_PATH.
    """
    conn = None
    final_db_path = db_path_to_use if db_path_to_use else DATABASE_PATH

    # Ensure directory exists
    db_dir = os.path.dirname(final_db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    try:
        conn = sqlite3.connect(final_db_path)
        cursor = conn.cursor()

        # Create Stock table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Stock (
                stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_name TEXT UNIQUE NOT NULL,
                quantity_quintals REAL NOT NULL
            );
        """)

        # Create GatePasses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GatePasses (
                gate_pass_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                party_name TEXT NOT NULL,
                address TEXT,
                vehicle_number TEXT,
                broker_name TEXT,
                amali_charge_per_quintal REAL,
                bag_charge_per_bag REAL,
                grand_total REAL
            );
        """)

        # Create GatePassOrderDetails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS GatePassOrderDetails (
                order_detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gate_pass_id INTEGER NOT NULL,
                lot_name TEXT NOT NULL,
                brand TEXT,
                num_bags INTEGER NOT NULL,
                weight_per_bag_kg REAL NOT NULL,
                price_per_quintal REAL NOT NULL,
                FOREIGN KEY (gate_pass_id) REFERENCES GatePasses(gate_pass_id)
            );
        """)

        # Create Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gate_pass_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                lot_name TEXT,
                quantity_quintals REAL,
                price_per_quintal REAL,
                debit_amount REAL,
                credit_amount REAL,
                FOREIGN KEY (gate_pass_id) REFERENCES GatePasses(gate_pass_id)
            );
        """)

        conn.commit()
        print(f"Tables created successfully in {final_db_path}")

    except sqlite3.Error as e:
        print(f"Error creating tables in {final_db_path}: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # When run directly, creates DB in the same directory as this script.
    print(f"Running database_setup.py standalone, creating DB at default path: {DATABASE_PATH}")
    create_tables()
