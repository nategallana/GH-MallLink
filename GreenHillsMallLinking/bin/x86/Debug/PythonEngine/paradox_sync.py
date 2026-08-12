import os
import sqlite3
import sys
import traceback

try:
    from pypxlib import Table as PxTable
except ImportError:
    print("ERROR: pypxlib module is not installed. Run 'pip install pypxlib'", file=sys.stderr)
    sys.exit(1)

# Centralized Password Definition (Fallback if needed, otherwise omitted)
DB_PASSWORD = "5A*281"


def find_table_file(paradox_dir, base_name):
    """
    Finds a Paradox table file in paradox_dir matching base_name regardless of
    case or extension. Prefers .DB files over .PX or extensionless files.
    """
    if not os.path.exists(paradox_dir):
        return None

    target_lower = base_name.lower()
    candidates = []

    for file in os.listdir(paradox_dir):
        file_base, file_ext = os.path.splitext(file)
        if file_base.lower() == target_lower:
            ext = file_ext.lower()
            if ext == ".db":
                candidates.insert(0, os.path.join(paradox_dir, file))   # Prefer .DB
            elif ext in [".px", ""]:
                candidates.append(os.path.join(paradox_dir, file))        # Fallback

    return candidates[0] if candidates else None


def ensure_database_schema(sqlite_cursor):
    """Creates SQLite staging tables for active and backup Paradox tables."""
    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS SyncHistories (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            StartedAt TEXT,
            CompletedAt TEXT,
            Status TEXT,
            OrdersSynced INTEGER,
            ItemsSynced INTEGER,
            ErrorDetails TEXT
        )
    """)

    # Active Tables
    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxOrders (
            OrderNo TEXT PRIMARY KEY, Time TEXT, AcDate TEXT, NoGuest INTEGER,
            Price REAL, Gst REAL, Disc_amt REAL, Disc_per REAL, Printed TEXT,
            Posted TEXT, Total REAL, Serv REAL, DiscType TEXT, Void TEXT,
            String1 TEXT, OrderNo2 TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxItems (
            Id INTEGER PRIMARY KEY AUTOINCREMENT, OrderNo TEXT, MenuKey TEXT,
            Status TEXT, MenuNo TEXT, ItemNo TEXT, Qty INTEGER, Size TEXT,
            PriceBefDisc REAL, DiscValue REAL, Discount REAL, DiscCode TEXT, DiscName TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxPayments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT, OrderNo TEXT, SeqNo INTEGER,
            PayID TEXT, PayName TEXT, Amount REAL, OrgAmount REAL, ExRate REAL,
            PayDT TEXT, Change REAL, PayName2 TEXT
        )
    """)

    # Backup Tables
    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxOrdersBkup (
            OrderNo TEXT PRIMARY KEY, Time TEXT, AcDate TEXT, NoGuest INTEGER,
            Price REAL, GST REAL, PST REAL, Disc_amt REAL, Disc_per REAL,
            Printed TEXT, Posted TEXT, Total REAL, Serv REAL, DiscType TEXT,
            String1 TEXT, OrderNo2 TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxItemsBkup (
            Id INTEGER PRIMARY KEY AUTOINCREMENT, OrderNo TEXT, MenuKey TEXT,
            Status TEXT, MenuNo TEXT, ItemNo TEXT, Qty INTEGER, Size TEXT,
            PriceBefDisc REAL, DiscValue REAL, Discount REAL, DiscCode TEXT, DiscName TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ParadoxPaymentsBkup (
            Id INTEGER PRIMARY KEY AUTOINCREMENT, OrderNo TEXT, SeqNo INTEGER,
            PayID TEXT, PayName TEXT, Amount REAL, OrgAmount REAL, ExRate REAL,
            PayDT TEXT, Change REAL, PayName2 TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS Configurations (
            Key TEXT PRIMARY KEY,
            Value TEXT
        )
    """)

    sqlite_cursor.execute("""
        CREATE TABLE IF NOT EXISTS GrandTotalTrackers (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            TargetDate TEXT,
            OldGrandTotal TEXT DEFAULT '0.00',
            NewGrandTotal TEXT DEFAULT '0.00',
            DayGrossSales TEXT DEFAULT '0.00',
            PreviousZCount INTEGER DEFAULT 0,
            NewZCount INTEGER DEFAULT 0,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


def get_col_val(row, field_name, default=""):
    """
    Safely reads a field value off a pypxlib Row object.

    IMPORTANT: Row is NOT a dict. It does not reliably support `in` or
    `.items()`. Using those falls back to Python's legacy sequence
    protocol (row[0], row[1], ...) which can raise KeyError instead of
    IndexError on this object -- and that KeyError (e.g. KeyError: 0)
    was silently killing every row read (str(KeyError(0)) == "0", which
    is exactly what showed up in the logs as "[ERROR] Reading rows
    from itembkup: 0").

    Fix: try direct item access, then attribute access, and treat any
    failure as "field not present" rather than crashing the whole row.
    """
    val = None
    try:
        val = row[field_name]
    except Exception:
        try:
            val = getattr(row, field_name)
        except Exception:
            val = None

    if val is None:
        return default

    return str(val).strip()


def sync_paradox_file(sqlite_cursor, paradox_dir, db_filename, target_table):
    """Directly parses a .DB file using pypxlib and writes to SQLite."""
    file_path = find_table_file(paradox_dir, db_filename)

    if not file_path:
        print(f"[WARN] File '{db_filename}' not found in '{paradox_dir}'")
        return 0

    print(f"[INFO] Processing '{os.path.basename(file_path)}' -> Target Table: '{target_table}'")

    # ─── Open Paradox file BEFORE touching SQLite so we don't wipe data on failure ───
    try:
        px_table = PxTable(file_path)
    except Exception as open_ex:
        print(f"[WARN] Opening without password failed for '{os.path.basename(file_path)}': {open_ex}")
        opened = False
        try:
            px_table = PxTable(file_path, DB_PASSWORD)
            opened = True
        except Exception as ex_pos:
            try:
                px_table = PxTable(file_path, password=DB_PASSWORD)
                opened = True
            except Exception as ex_kw:
                print(f"[WARN] Opening with password attempts failed: {ex_pos} | {ex_kw}")

        if not opened:
            print(f"[ERROR] Unable to open Paradox file '{file_path}' even with password. Skipping.")
            return 0

    # ─── NOW it is safe to clear the target table ───
    sqlite_cursor.execute(f"DELETE FROM {target_table}")

    count = 0
    row_index = -1
    try:
        for row in px_table:
            row_index += 1
            order_no = get_col_val(row, 'OrderNo') or get_col_val(row, 'ORDERNO') or get_col_val(row, 'orderno')
            if not order_no:
                continue

            # --- ORDERS (Active & Backup) ---
            if target_table in ["ParadoxOrders", "ParadoxOrdersBkup"]:
                pst_val = float(get_col_val(row, 'Pst', 0.0) or 0.0)

                if target_table == "ParadoxOrders":
                    sqlite_cursor.execute("""
                        INSERT INTO ParadoxOrders (OrderNo, Time, AcDate, NoGuest, Price, Gst, Disc_amt, Disc_per, Printed, Posted, Total, Serv, DiscType, Void, String1, OrderNo2)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(OrderNo) DO UPDATE SET
                            Time=excluded.Time, AcDate=excluded.AcDate, Total=excluded.Total, Disc_amt=excluded.Disc_amt, Void=excluded.Void
                    """, (
                        order_no,
                        get_col_val(row, 'Time'),
                        get_col_val(row, 'AcDate'),
                        int(float(get_col_val(row, 'NoGuest', 0) or 0)),
                        float(get_col_val(row, 'Price', 0.0) or 0.0),
                        float(get_col_val(row, 'Gst', 0.0) or 0.0),
                        float(get_col_val(row, 'Disc_amt', 0.0) or 0.0),
                        float(get_col_val(row, 'Disc_per', 0.0) or 0.0),
                        get_col_val(row, 'Printed'),
                        get_col_val(row, 'Posted'),
                        float(get_col_val(row, 'Total', 0.0) or 0.0),
                        float(get_col_val(row, 'Serv', 0.0) or 0.0),
                        get_col_val(row, 'DiscType'),
                        get_col_val(row, 'Void'),
                        get_col_val(row, 'String1'),
                        get_col_val(row, 'OrderNo2')
                    ))
                else:  # ParadoxOrdersBkup
                    sqlite_cursor.execute("""
                        INSERT INTO ParadoxOrdersBkup (OrderNo, Time, AcDate, NoGuest, Price, GST, PST, Disc_amt, Disc_per, Printed, Posted, Total, Serv, DiscType, String1, OrderNo2)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(OrderNo) DO UPDATE SET
                            Time=excluded.Time, AcDate=excluded.AcDate, Total=excluded.Total, Disc_amt=excluded.Disc_amt
                    """, (
                        order_no,
                        get_col_val(row, 'Time'),
                        get_col_val(row, 'AcDate'),
                        int(float(get_col_val(row, 'NoGuest', 0) or 0)),
                        float(get_col_val(row, 'Price', 0.0) or 0.0),
                        float(get_col_val(row, 'Gst', 0.0) or 0.0),
                        pst_val,
                        float(get_col_val(row, 'Disc_amt', 0.0) or 0.0),
                        float(get_col_val(row, 'Disc_per', 0.0) or 0.0),
                        get_col_val(row, 'Printed'),
                        get_col_val(row, 'Posted'),
                        float(get_col_val(row, 'Total', 0.0) or 0.0),
                        float(get_col_val(row, 'Serv', 0.0) or 0.0),
                        get_col_val(row, 'DiscType'),
                        get_col_val(row, 'String1'),
                        get_col_val(row, 'OrderNo2')
                    ))
                count += 1

            # --- ITEMS (Active & Backup) ---
            elif target_table in ["ParadoxItems", "ParadoxItemsBkup"]:
                sql_query = f"""
                    INSERT INTO {target_table} (OrderNo, MenuKey, Status, MenuNo, ItemNo, Qty, Size, PriceBefDisc, DiscValue, Discount, DiscCode, DiscName)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                sqlite_cursor.execute(sql_query, (
                    order_no,
                    get_col_val(row, 'MenuKey'),
                    get_col_val(row, 'Status'),
                    get_col_val(row, 'MenuNo'),
                    get_col_val(row, 'ItemNo'),
                    int(float(get_col_val(row, 'Qty', 1) or 1)),
                    get_col_val(row, 'Size'),
                    float(get_col_val(row, 'PriceBefDisc', 0.0) or 0.0),
                    float(get_col_val(row, 'DiscValue', 0.0) or 0.0),
                    get_col_val(row, 'Discount'),
                    get_col_val(row, 'DiscCode'),
                    get_col_val(row, 'DiscName')
                ))
                count += 1

            # --- PAYMENTS (Active & Backup) ---
            elif target_table in ["ParadoxPayments", "ParadoxPaymentsBkup"]:
                sql_query = f"""
                    INSERT INTO {target_table} (OrderNo, SeqNo, PayID, PayName, Amount, OrgAmount, ExRate, PayDT, Change, PayName2)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                sqlite_cursor.execute(sql_query, (
                    order_no,
                    int(float(get_col_val(row, 'SeqNo', 0) or 0)),
                    get_col_val(row, 'PayID'),
                    get_col_val(row, 'PayName'),
                    float(get_col_val(row, 'Amount', 0.0) or 0.0),
                    float(get_col_val(row, 'OrgAmount', 0.0) or 0.0),
                    float(get_col_val(row, 'ExRate', 1.0) or 1.0),
                    get_col_val(row, 'PayDT'),
                    float(get_col_val(row, 'Change', 0.0) or 0.0),
                    get_col_val(row, 'PayName2')
                ))
                count += 1

        print(f"[SUCCESS] Read {count} rows from '{os.path.basename(file_path)}'")
    except Exception as ex:
        # Print the FULL traceback (not just str(ex)) so failures are diagnosable,
        # and report which row index it died on.
        print(f"[ERROR] Reading rows from {db_filename} (failed at row index {row_index}, {count} rows committed so far): {ex}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        try:
            px_table.close()
        except Exception:
            pass

    return count


def sync_paradox(sqlite_db_path, paradox_dir, allowed_tables=None, password=DB_PASSWORD):
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # Make sure SQLite tables exist
    ensure_database_schema(cursor)

    tables_map = [
        ("Orders", "ParadoxOrders"),
        ("OrdItem", "ParadoxItems"),
        ("OrdPay", "ParadoxPayments"),
        ("Ordbkup", "ParadoxOrdersBkup"),
        ("itembkup", "ParadoxItemsBkup"),
        ("OrdPayBK", "ParadoxPaymentsBkup")
    ]

    total_orders = 0
    total_items = 0
    total_payments = 0

    for db_filename, target_table in tables_map:
        # Skip tables not in the allowed filter (when C# tells us to only sync failures)
        if allowed_tables and target_table not in allowed_tables:
            continue

        synced = sync_paradox_file(cursor, paradox_dir, db_filename, target_table)

        if "Orders" in target_table:
            total_orders += synced
        elif "Items" in target_table:
            total_items += synced
        elif "Payments" in target_table:
            total_payments += synced

    conn.commit()
    conn.close()

    print(f"SUCCESS: Synced {total_orders} orders, {total_items} items, and {total_payments} payments from Paradox files.")
    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paradox to SQLite Sync Engine")
    parser.add_argument("--action", type=str, help="Action name (e.g. sync_paradox)")
    parser.add_argument("--db", type=str, default="gh_mall_linking.db", help="Path to SQLite DB")
    parser.add_argument("--paradox_dir", type=str, help="Path to Paradox files")
    parser.add_argument("--password", type=str, default=DB_PASSWORD, help="Paradox DB password")
    parser.add_argument("--tables", type=str, default="", help="Comma-separated target tables to sync (e.g. ParadoxItemsBkup,ParadoxPaymentsBkup)")

    args, unknown = parser.parse_known_args()

    p_dir = args.paradox_dir
    p_db = args.db
    p_pass = args.password

    for arg in sys.argv[1:]:
        clean = arg.strip('"').strip("'")
        if os.path.isdir(clean):
            p_dir = clean
        elif clean.endswith(".db") or clean.endswith(".sqlite"):
            p_db = clean

    # Parse optional table filter from C#
    allowed = None
    if args.tables:
        allowed = [t.strip() for t in args.tables.split(",")]

    print(f"Executing Sync -> DB: {p_db} | Paradox Dir: {p_dir}")
    sync_paradox(p_db, p_dir, allowed_tables=allowed, password=p_pass)