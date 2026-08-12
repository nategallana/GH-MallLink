import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import re

def ensure_unified_schema(cursor):
    """Creates unified staging tables for both Paradox and Cloud XML sources."""
    # FIX: StagingOrders' primary key was OrderNo alone. Paradox and Cloud export
    # the SAME order numbers for the same physical transactions -- whichever
    # source synced SECOND collided on that key, and ON CONFLICT overwrote
    # Time/Total/Void/etc with the new source's values WITHOUT updating Source,
    # silently mislabeling every row as whichever source synced first. Composite
    # key (OrderNo, Source) lets both sources' rows for the same order coexist.
    # FOREIGN KEY refs to StagingOrders(OrderNo) dropped -- a single-column FK
    # can no longer match a composite-key parent.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StagingOrders (
            OrderNo TEXT NOT NULL,
            Source TEXT NOT NULL,         -- 'PARADOX' or 'CLOUD'
            Time TEXT,
            AcDate TEXT,
            NoGuest INTEGER DEFAULT 0,
            Price REAL DEFAULT 0.0,
            Gst REAL DEFAULT 0.0,
            Pst REAL DEFAULT 0.0,
            Disc_amt REAL DEFAULT 0.0,
            Disc_per REAL DEFAULT 0.0,
            Serv REAL DEFAULT 0.0,
            Total REAL DEFAULT 0.0,
            DiscType TEXT,
            Void TEXT DEFAULT '0',
            Printed TEXT,
            Posted TEXT,
            String1 TEXT,
            OrderNo2 TEXT,
            SyncedAt TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (OrderNo, Source)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StagingItems (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderNo TEXT NOT NULL,
            Source TEXT NOT NULL,         -- 'PARADOX' or 'CLOUD'
            MenuKey TEXT,
            Status TEXT,
            MenuNo TEXT,
            ItemNo TEXT,
            Description TEXT,
            Qty REAL DEFAULT 1.0,
            Size TEXT,
            PriceBefDisc REAL DEFAULT 0.0,
            DiscValue REAL DEFAULT 0.0,
            Discount REAL DEFAULT 0.0,
            DiscCode TEXT,
            DiscName TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StagingPayments (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            OrderNo TEXT NOT NULL,
            Source TEXT NOT NULL,         -- 'PARADOX' or 'CLOUD'
            SeqNo INTEGER DEFAULT 0,
            PayID TEXT,
            PayName TEXT,
            Amount REAL DEFAULT 0.0,
            OrgAmount REAL DEFAULT 0.0,
            ExRate REAL DEFAULT 1.0,
            PayDT TEXT,
            Change REAL DEFAULT 0.0,
            PayName2 TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Configurations (
            Key TEXT PRIMARY KEY,
            Value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS GrandTotalTrackers (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            TargetDate TEXT UNIQUE,
            OldGrandTotal TEXT DEFAULT '0.00',
            NewGrandTotal TEXT DEFAULT '0.00',
            DayGrossSales TEXT DEFAULT '0.00',
            PreviousZCount INTEGER DEFAULT 0,
            NewZCount INTEGER DEFAULT 0,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
    
    print(f"[AUTO-REGISTER] Registered new payment method: '{pay_name_clean}'")

def classify_xml_file(file_path):
    name_upper = os.path.basename(file_path).upper()
    if "POSTORDER" in name_upper:
        return "postorder"
    if "VOIDORDER" in name_upper:
        return "voidorder"

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        if root.tag == "Order":
            return "postorder"
        if root.tag == "Request":
            return "voidorder"
    except Exception:
        pass

    return None

def parse_acdate(acdate_raw):
    if not acdate_raw or len(acdate_raw) != 8:
        return None
    return f"{acdate_raw[0:4]}-{acdate_raw[4:6]}-{acdate_raw[6:8]}"

def parse_time(created_raw):
    if not created_raw or "T" not in created_raw:
        return ""
    time_part = created_raw.split("T", 1)[1]
    for sep in ("+", "-"):
        idx = time_part.find(sep)
        if idx > 0:
            time_part = time_part[:idx]
            break
    digits = time_part.replace(":", "")
    if len(digits) >= 6:
        return f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}"
    return time_part

def find_all_xml_files(base_dir):
    found = []
    for root, _dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(".xml"):
                found.append(os.path.join(root, f))
    return found

VOID_ORDER_PATTERN = re.compile(r'orderid=["\']([^"\']+)["\']', re.IGNORECASE)

def collect_voided_order_nos(search_files):
    voided = set()
    for file_path in search_files:
        if "VOIDORDER" not in os.path.basename(file_path).upper():
            continue
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = VOID_ORDER_PATTERN.findall(content)
                for match in matches:
                    voided.add(match.strip())
        except Exception:
            pass
    return voided

def parse_post_order_file(file_path, voided_order_nos):
    tree = ET.parse(file_path)
    order_el = tree.getroot()
    if order_el.tag != "Order":
        return None

    items_el = order_el.find("Items")
    if items_el is None or len(items_el) == 0:
        return "non_sale"

    order_no = order_el.get("orderNo", "").strip()
    if not order_no:
        return None

    acdate = parse_acdate(order_el.get("accDate", ""))
    time_str = parse_time(order_el.get("created", ""))

    total = float(order_el.get("total", "0") or 0.0)
    price = float(order_el.get("subtotal", "0") or 0.0)
    serv = float(order_el.get("serviceCharge", "0") or 0.0)
    no_guest = int(float(order_el.get("guests", "0") or 0))
    own_void_flag = order_el.get("void", "0").strip() == "1"

    gst = 0.0
    taxes_el = order_el.find("Taxes")
    if taxes_el is not None:
        for tax_el in taxes_el.findall("Tax"):
            gst += float(tax_el.get("amount", "0") or 0.0)

    disc_amt = 0.0
    disc_types = []
    discounts_el = order_el.find("Discounts")
    if discounts_el is not None:
        for disc_el in discounts_el.findall("Discount"):
            disc_amt += abs(float(disc_el.get("value", "0") or 0.0))
            dtype = disc_el.get("type", "").strip()
            if dtype:
                disc_types.append(dtype)
    disc_type = ",".join(disc_types)

    is_void = "1" if (own_void_flag or order_no in voided_order_nos) else "0"

    items = []
    for item_el in items_el.findall("Item"):
        items.append({
            "ItemNo": item_el.get("ItemNo", ""),
            "MenuNo": item_el.get("MenuNo", ""),
            "Description": item_el.get("MenuName", ""),
            "PriceBefDisc": float(item_el.get("PriceBefDisc", "0") or 0.0),
            "Qty": float(item_el.get("Qty", "1") or 1.0),
            "DiscValue": float(item_el.get("DiscAmount", "0") or 0.0),
        })

    payments = []
    payments_el = order_el.find("Payments")
    if payments_el is not None:
        for pay_el in payments_el.findall("Payment"):
            pay_name = pay_el.get("name") or pay_el.get("PayName") or pay_el.get("Name") or ""
            payments.append({
                "PayName": pay_name,
                "Amount": float(pay_el.get("amount", "0") or pay_el.get("Amount", "0") or 0.0),
            })

    return {
        "OrderNo": order_no, "Time": time_str, "AcDate": acdate, "NoGuest": no_guest,
        "Price": price, "Gst": gst, "Disc_amt": disc_amt, "Serv": serv, "Total": total,
        "DiscType": disc_type, "Void": is_void, "Items": items, "Payments": payments,
    }

def sync_cloud_xml(sqlite_db_path, cloud_dir, target_date=None):
    if not os.path.exists(cloud_dir):
        print(f"ERROR: Cloud data folder does not exist: {cloud_dir}", file=sys.stderr)
        return False

    conn = sqlite3.connect(sqlite_db_path, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    ensure_unified_schema(cursor)

    xml_files = []
    if target_date:
        formatted_date_folder = target_date.replace("-", "")
        date_folder = os.path.join(cloud_dir, target_date)
        alt_date_folder = os.path.join(cloud_dir, formatted_date_folder)

        if os.path.exists(date_folder):
            xml_files = find_all_xml_files(date_folder)
        elif os.path.exists(alt_date_folder):
            xml_files = find_all_xml_files(alt_date_folder)
        else:
            xml_files = find_all_xml_files(cloud_dir)

        cursor.execute("DELETE FROM StagingItems WHERE OrderNo IN (SELECT OrderNo FROM StagingOrders WHERE AcDate = ? AND Source = 'CLOUD')", (target_date,))
        cursor.execute("DELETE FROM StagingPayments WHERE OrderNo IN (SELECT OrderNo FROM StagingOrders WHERE AcDate = ? AND Source = 'CLOUD')", (target_date,))
        cursor.execute("DELETE FROM StagingOrders WHERE AcDate = ? AND Source = 'CLOUD'", (target_date,))
    else:
        xml_files = find_all_xml_files(cloud_dir)
        cursor.execute("DELETE FROM StagingItems WHERE Source = 'CLOUD'")
        cursor.execute("DELETE FROM StagingPayments WHERE Source = 'CLOUD'")
        cursor.execute("DELETE FROM StagingOrders WHERE Source = 'CLOUD'")

    voided_order_nos = collect_voided_order_nos(xml_files)

    orders_synced = 0
    items_synced = 0
    payments_synced = 0
    skipped_non_sale = 0
    skipped_date_mismatch = 0
    errors = 0

    for file_path in xml_files:
        if classify_xml_file(file_path) != "postorder":
            continue

        try:
            parsed = parse_post_order_file(file_path, voided_order_nos)
            if parsed is None:
                continue
            if parsed == "non_sale":
                skipped_non_sale += 1
                continue

            if target_date and parsed["AcDate"] != target_date:
                skipped_date_mismatch += 1
                continue

            cursor.execute("""
                INSERT INTO StagingOrders (OrderNo, Source, Time, AcDate, NoGuest, Price, Gst, Disc_amt, Serv, Total, DiscType, Void)
                VALUES (?, 'CLOUD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(OrderNo, Source) DO UPDATE SET
                    Time=excluded.Time, AcDate=excluded.AcDate, Total=excluded.Total,
                    Disc_amt=excluded.Disc_amt, Void=excluded.Void
            """, (parsed["OrderNo"], parsed["Time"], parsed["AcDate"], parsed["NoGuest"],
                  parsed["Price"], parsed["Gst"], parsed["Disc_amt"], parsed["Serv"],
                  parsed["Total"], parsed["DiscType"], parsed["Void"]))
            orders_synced += 1

            for item in parsed["Items"]:
                cursor.execute("""
                    INSERT INTO StagingItems (OrderNo, Source, ItemNo, MenuNo, Description, PriceBefDisc, Qty, DiscValue)
                    VALUES (?, 'CLOUD', ?, ?, ?, ?, ?, ?)
                """, (parsed["OrderNo"], item["ItemNo"], item["MenuNo"], item["Description"],
                      item["PriceBefDisc"], item["Qty"], item["DiscValue"]))
                items_synced += 1

            for payment in parsed["Payments"]:
                ensure_payment_method_exists(cursor, payment["PayName"])
                cursor.execute("""
                    INSERT INTO StagingPayments (OrderNo, Source, PayName, Amount)
                    VALUES (?, 'CLOUD', ?, ?)
                """, (parsed["OrderNo"], payment["PayName"], payment["Amount"]))
                payments_synced += 1

        except Exception as ex:
            errors += 1
            print(f"[ERROR] Failed to process '{file_path}': {ex}", file=sys.stderr)

    conn.commit()
    conn.close()

    print(
        f"SUCCESS: Synced {orders_synced} orders, {items_synced} items, {payments_synced} payments to Staging tables. "
        f"Skipped {skipped_non_sale} non-sale entries, {skipped_date_mismatch} date mismatches, {errors} errors."
    )
    return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        td = sys.argv[3] if len(sys.argv) >= 4 else None
        sync_cloud_xml(sys.argv[1], sys.argv[2], target_date=td)
    else:
        print("Usage: python xml_sync.py <db_path> <cloud_data_base_folder> [target_date YYYY-MM-DD]")