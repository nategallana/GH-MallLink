import os
import sqlite3
import sys
import traceback

try:
    from pypxlib import Table as PxTable
except ImportError:
    print("ERROR: pypxlib module is not installed. Run 'pip install pypxlib'", file=sys.stderr)
    sys.exit(1)

DB_PASSWORD = "5A*281"

def find_table_file(paradox_dir, base_names):
    """
    Searches paradox_dir for the first matching file from base_names list.
    Supports both active DB files (ORDERS.DB) and backup DB files (ordbkup.DB).
    """
    if not os.path.exists(paradox_dir):
        return None

    if isinstance(base_names, str):
        base_names = [base_names]

    target_lowers = [b.lower() for b in base_names]

    for target in target_lowers:
        for file in os.listdir(paradox_dir):
            file_base, file_ext = os.path.splitext(file)
            if file_base.lower() == target and file_ext.lower() == ".db":
                return os.path.join(paradox_dir, file)

    return None

def ensure_payment_method_exists(cursor, raw_pay_name):
    if not raw_pay_name or not str(raw_pay_name).strip():
        return

    pay_name_clean = str(raw_pay_name).strip().upper()

    cursor.execute("SELECT Id FROM PaymentMethods WHERE UPPER(MethodName) = ?", (pay_name_clean,))
    if cursor.fetchone():
        return

    cursor.execute("SELECT Id FROM PaymentMethodKeywords WHERE ? LIKE '%' || UPPER(Keyword) || '%'", (pay_name_clean,))
    if cursor.fetchone():
        return

    cursor.execute("""
        INSERT INTO PaymentMethods (MethodName, GhCode, IsDefault, IsActive, CreatedAt)
        VALUES (?, '99', 0, 1, DATETIME('now'))
    """, (pay_name_clean,))
    
    new_method_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO PaymentMethodKeywords (PaymentMethodId, Keyword)
        VALUES (?, ?)
    """, (new_method_id, pay_name_clean))
    
    print(f"[AUTO-REGISTER] Registered new Paradox payment method: '{pay_name_clean}'")

def get_col_val(row, field_name, default=""):
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

def sync_paradox_file(sqlite_cursor, paradox_dir, db_filenames, table_type):
    file_path = find_table_file(paradox_dir, db_filenames)

    if not file_path:
        print(f"[WARN] None of the files {db_filenames} were found in '{paradox_dir}'")
        return 0

    print(f"[INFO] Syncing {table_type.upper()} from file: {file_path}")

    px_table = None
    try:
        px_table = PxTable(file_path, DB_PASSWORD)
    except Exception:
        try:
            px_table = PxTable(file_path)
        except Exception as ex:
            print(f"[ERROR] Could not open Paradox file '{file_path}': {ex}")
            return 0

    count = 0
    try:
        # Load ALL records into memory instantly to avoid slow file seeking
        records = px_table.get_records()
        print(f"[INFO] Fast-loaded {len(records)} records from {table_type.upper()}")

        for row in records:
            # Flexible dictionary getter
            def get_val(key, default=""):
                val = row.get(key)
                if val is None:
                    # Case-insensitive fallback lookup
                    for k, v in row.items():
                        if k.lower() == key.lower():
                            val = v
                            break
                return str(val).strip() if val is not None else default

            order_no = (
                get_val('OrderNo') or 
                get_val('ORDERNO') or 
                get_val('Order_No')
            )

            if not order_no:
                continue

            # --- ORDERS ---
            if table_type == "orders":
                pst_val = float(get_val('PST', 0.0) or get_val('Pst', 0.0) or 0.0)
                gst_val = float(get_val('GST', 0.0) or get_val('Gst', 0.0) or 0.0)
                sqlite_cursor.execute("""
                    INSERT INTO StagingOrders (
                        OrderNo, Source, Time, AcDate, NoGuest, Price, Gst, Pst,
                        Disc_amt, Disc_per, Printed, Posted, Total, Serv, DiscType, Void, String1, OrderNo2
                    ) VALUES (?, 'PARADOX', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(OrderNo, Source) DO UPDATE SET
                        Time=excluded.Time, AcDate=excluded.AcDate, Total=excluded.Total,
                        Disc_amt=excluded.Disc_amt, Void=excluded.Void
                """, (
                    order_no,
                    get_val('Time'),
                    get_val('AcDate') or get_val('Date'),
                    int(float(get_val('NoGuest', 0) or 0)),
                    float(get_val('Price', 0.0) or 0.0),
                    gst_val,
                    pst_val,
                    float(get_val('Disc_amt', 0.0) or 0.0),
                    float(get_val('Disc_per', 0.0) or 0.0),
                    get_val('Printed'),
                    get_val('Posted'),
                    float(get_val('Total', 0.0) or 0.0),
                    float(get_val('Serv', 0.0) or 0.0),
                    get_val('DiscType'),
                    get_val('Void', '0'),
                    get_val('String1'),
                    get_val('OrderNo2')
                ))
                count += 1

            # --- ITEMS ---
            elif table_type == "items":
                sqlite_cursor.execute("""
                    INSERT INTO StagingItems (
                        OrderNo, Source, MenuKey, Status, MenuNo, ItemNo, Description, Qty, Size, PriceBefDisc, DiscValue, Discount, DiscCode, DiscName
                    ) VALUES (?, 'PARADOX', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_no,
                    get_val('MenuKey'),
                    get_val('Status'),
                    get_val('MenuNo'),
                    get_val('ItemNo'),
                    get_val('Description') or get_val('String1'),
                    float(get_val('Qty', 1) or 1.0),
                    get_val('Size'),
                    float(get_val('PriceBefDisc', 0.0) or get_val('Price', 0.0) or 0.0),
                    float(get_val('DiscValue', 0.0) or 0.0),
                    float(get_val('Discount', 0.0) or 0.0),
                    get_val('DiscCode'),
                    get_val('DiscName')
                ))
                count += 1

            # --- PAYMENTS ---
            elif table_type == "payments":
                pay_name = get_val('PayName')
                ensure_payment_method_exists(sqlite_cursor, pay_name)

                sqlite_cursor.execute("""
                    INSERT INTO StagingPayments (
                        OrderNo, Source, SeqNo, PayID, PayName, Amount, OrgAmount, ExRate, PayDT, Change, PayName2
                    ) VALUES (?, 'PARADOX', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_no,
                    int(float(get_val('SeqNo', 0) or 0)),
                    get_val('PayID'),
                    pay_name,
                    float(get_val('Amount', 0.0) or 0.0),
                    float(get_val('OrgAmount', 0.0) or 0.0),
                    float(get_val('ExRate', 1.0) or 1.0),
                    get_val('PayDT'),
                    float(get_val('Change', 0.0) or 0.0),
                    get_val('PayName2')
                ))
                count += 1

    except Exception as ex:
        print(f"[ERROR] Sync failed for {table_type.upper()}: {ex}", file=sys.stderr)
    finally:
        if px_table:
            try:
                px_table.close()
            except Exception:
                pass

    return count
def sync_paradox(sqlite_db_path, paradox_dir, allowed_tables=None, password=DB_PASSWORD):
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    from xml_sync import ensure_unified_schema
    ensure_unified_schema(cursor)

    cursor.execute("DELETE FROM StagingItems WHERE Source = 'PARADOX'")
    cursor.execute("DELETE FROM StagingPayments WHERE Source = 'PARADOX'")
    cursor.execute("DELETE FROM StagingOrders WHERE Source = 'PARADOX'")

    # Only the backup files -- active tables (Orders/OrdItem/OrdPay) are never
    # read, per your request to drop that path entirely.
    orders = sync_paradox_file(cursor, paradox_dir, ["ordbkup"], "orders")
    items = sync_paradox_file(cursor, paradox_dir, ["itembkup"], "items")
    payments = sync_paradox_file(cursor, paradox_dir, ["ordpaybk"], "payments")

    conn.commit()
    conn.close()

    print(f"SUCCESS: Synced {orders} orders, {items} items, and {payments} payments from Paradox files.")
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Paradox to SQLite Sync Engine")
    parser.add_argument("--action", type=str, help="Action name")
    parser.add_argument("--db", type=str, default="gh_mall_linking.db", help="Path to SQLite DB")
    parser.add_argument("--paradox_dir", type=str, help="Path to Paradox files")
    parser.add_argument("--password", type=str, default=DB_PASSWORD, help="Paradox DB password")

    args, _ = parser.parse_known_args()
    if args.paradox_dir and args.db:
        sync_paradox(args.db, args.paradox_dir, password=args.password)