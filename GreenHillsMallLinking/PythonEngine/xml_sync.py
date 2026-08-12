import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
import re


# ============================================================
# SCHEMA
# ============================================================

def ensure_unified_schema(cursor):

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StagingOrders (
            OrderNo TEXT NOT NULL,
            Source TEXT NOT NULL,
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
            Source TEXT NOT NULL,
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
            Source TEXT NOT NULL,
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


# ============================================================
# PAYMENT METHODS
# ============================================================

def ensure_payment_method_exists(
    cursor,
    raw_pay_name
):

    if not raw_pay_name:
        return

    pay_name_clean = str(
        raw_pay_name
    ).strip().upper()

    if not pay_name_clean:
        return

    cursor.execute("""
        SELECT Id
        FROM PaymentMethods
        WHERE UPPER(MethodName) = ?
        LIMIT 1
    """, (pay_name_clean,))

    if cursor.fetchone():
        return

    cursor.execute("""
        SELECT Id
        FROM PaymentMethodKeywords
        WHERE UPPER(Keyword) = ?
        LIMIT 1
    """, (pay_name_clean,))

    if cursor.fetchone():
        return

    cursor.execute("""
        INSERT INTO PaymentMethods (
            MethodName,
            GhCode,
            IsDefault,
            IsActive,
            CreatedAt
        )
        VALUES (
            ?,
            '99',
            0,
            1,
            DATETIME('now')
        )
    """, (pay_name_clean,))

    new_method_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO PaymentMethodKeywords (
            PaymentMethodId,
            Keyword
        )
        VALUES (?, ?)
    """, (
        new_method_id,
        pay_name_clean
    ))

    print(
        f"[AUTO-REGISTER] "
        f"Registered Cloud payment method: "
        f"'{pay_name_clean}'"
    )


# ============================================================
# FILE HELPERS
# ============================================================

def classify_xml_file(file_path):

    name_upper = os.path.basename(
        file_path
    ).upper()

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

    if not acdate_raw:
        return None

    value = str(acdate_raw).strip()

    if len(value) == 8 and value.isdigit():

        return (
            f"{value[0:4]}-"
            f"{value[4:6]}-"
            f"{value[6:8]}"
        )

    return value


def parse_time(created_raw):

    if not created_raw:
        return ""

    value = str(
        created_raw
    ).strip()

    if "T" not in value:
        return value[:8]

    time_part = value.split(
        "T",
        1
    )[1]

    for sep in ("+", "-"):

        index = time_part.find(sep)

        if index > 0:
            time_part = time_part[:index]
            break

    digits = time_part.replace(
        ":",
        ""
    )

    if len(digits) >= 6:

        return (
            f"{digits[0:2]}:"
            f"{digits[2:4]}:"
            f"{digits[4:6]}"
        )

    return time_part


def find_all_xml_files(base_dir):

    found = []

    for root, _dirs, files in os.walk(
        base_dir
    ):

        for file_name in files:

            if file_name.lower().endswith(
                ".xml"
            ):

                found.append(
                    os.path.join(
                        root,
                        file_name
                    )
                )

    return found


# ============================================================
# VOID ORDER DETECTION
# ============================================================

VOID_ORDER_PATTERN = re.compile(
    r'orderid=["\']([^"\']+)["\']',
    re.IGNORECASE
)


def collect_voided_order_nos(search_files):

    voided = set()

    for file_path in search_files:

        if "VOIDORDER" not in os.path.basename(
            file_path
        ).upper():
            continue

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                content = f.read()

                matches = VOID_ORDER_PATTERN.findall(
                    content
                )

                for match in matches:
                    voided.add(
                        match.strip()
                    )

        except Exception:
            pass

    return voided


# ============================================================
# NUMBER HELPER
# ============================================================

def number(value, default=0.0):

    try:

        if value is None:
            return default

        value = str(value).strip()

        if not value:
            return default

        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


def attr(el, *names, default=""):

    for name in names:

        value = el.get(name)

        if value is not None:
            return value

    return default


# ============================================================
# CLOUD ORDER PARSER
# ============================================================

def parse_post_order_file(
    file_path,
    voided_order_nos
):

    tree = ET.parse(file_path)

    order_el = tree.getroot()

    if order_el.tag != "Order":
        return None

    items_el = order_el.find(
        "Items"
    )

    if (
        items_el is None
        or len(items_el) == 0
    ):
        return "non_sale"

    order_no = attr(
        order_el,
        "orderNo",
        "OrderNo"
    ).strip()

    if not order_no:
        return None

    acdate = parse_acdate(
        attr(
            order_el,
            "accDate",
            "AcDate"
        )
    )

    time_str = parse_time(
        attr(
            order_el,
            "created",
            "Created"
        )
    )

    total = number(
        attr(
            order_el,
            "total",
            "Total"
        )
    )

    price = number(
        attr(
            order_el,
            "subtotal",
            "Subtotal",
            "Price"
        )
    )

    serv = number(
        attr(
            order_el,
            "serviceCharge",
            "ServiceCharge",
            "Serv"
        )
    )

    no_guest = int(
        number(
            attr(
                order_el,
                "guests",
                "Guests",
                "NoGuest"
            )
        )
    )

    own_void_flag = (
        attr(
            order_el,
            "void",
            "Void",
            default="0"
        ).strip() == "1"
    )

    # ========================================================
    # TAXES
    # ========================================================

    gst = 0.0

    taxes_el = order_el.find(
        "Taxes"
    )

    if taxes_el is not None:

        for tax_el in taxes_el.findall(
            "Tax"
        ):

            gst += number(
                attr(
                    tax_el,
                    "amount",
                    "Amount"
                )
            )

    # ========================================================
    # DISCOUNTS
    # ========================================================

    disc_amt = 0.0
    disc_types = []

    discounts_el = order_el.find(
        "Discounts"
    )

    if discounts_el is not None:

        for disc_el in discounts_el.findall(
            "Discount"
        ):

            disc_amt += abs(
                number(
                    attr(
                        disc_el,
                        "value",
                        "Value"
                    )
                )
            )

            dtype = attr(
                disc_el,
                "type",
                "Type"
            ).strip()

            if dtype:
                disc_types.append(
                    dtype
                )

    disc_type = ",".join(
        disc_types
    )

    is_void = (
        "1"
        if (
            own_void_flag
            or order_no in voided_order_nos
        )
        else "0"
    )

    # ========================================================
    # ITEMS
    # ========================================================

    items = []

    for item_el in items_el.findall(
        "Item"
    ):

        description = (
            attr(
                item_el,
                "MenuName",
                "Description",
                "Name"
            )
        )

        items.append({

            "MenuKey": attr(
                item_el,
                "MenuKey"
            ),

            "Status": attr(
                item_el,
                "Status"
            ),

            "MenuNo": attr(
                item_el,
                "MenuNo"
            ),

            "ItemNo": attr(
                item_el,
                "ItemNo"
            ),

            "Description": description,

            "Qty": number(
                attr(
                    item_el,
                    "Qty"
                ),
                1.0
            ),

            "Size": attr(
                item_el,
                "Size"
            ),

            "PriceBefDisc": number(
                attr(
                    item_el,
                    "PriceBefDisc",
                    "Price"
                )
            ),

            "DiscValue": number(
                attr(
                    item_el,
                    "DiscAmount",
                    "DiscValue"
                )
            ),

            "Discount": number(
                attr(
                    item_el,
                    "Discount",
                    "DiscAmount"
                )
            ),

            "DiscCode": attr(
                item_el,
                "DiscCode"
            ),

            "DiscName": attr(
                item_el,
                "DiscName"
            ),
        })

    # ========================================================
    # PAYMENTS
    # ========================================================

    payments = []

    payments_el = order_el.find(
        "Payments"
    )

    if payments_el is not None:

        for payment_el in payments_el.findall(
            "Payment"
        ):

            # IMPORTANT:
            # This is the Cloud payment name.
            # Preserve it exactly.
            pay_name = attr(
                payment_el,
                "name",
                "PayName",
                "Name"
            ).strip()

            payments.append({

                "PayID": attr(
                    payment_el,
                    "PayID",
                    "payId",
                    "id"
                ),

                "PayName": pay_name,

                "Amount": number(
                    attr(
                        payment_el,
                        "amount",
                        "Amount"
                    )
                ),

                "OrgAmount": number(
                    attr(
                        payment_el,
                        "OrgAmount",
                        "orgAmount",
                        "amount",
                        "Amount"
                    )
                ),

                "ExRate": number(
                    attr(
                        payment_el,
                        "ExRate",
                        "exRate"
                    ),
                    1.0
                ),

                "PayDT": attr(
                    payment_el,
                    "PayDT",
                    "payDate",
                    "date"
                ),

                "Change": number(
                    attr(
                        payment_el,
                        "Change",
                        "change"
                    )
                ),

                "PayName2": attr(
                    payment_el,
                    "PayName2",
                    "payName2"
                ),
            })

    return {

        "OrderNo": order_no,

        "Time": time_str,

        "AcDate": acdate,

        "NoGuest": no_guest,

        "Price": price,

        "Gst": gst,

        "Pst": 0.0,

        "Disc_amt": disc_amt,

        "Disc_per": 0.0,

        "Serv": serv,

        "Total": total,

        "DiscType": disc_type,

        "Void": is_void,

        "Printed": "",

        "Posted": "",

        "String1": "",

        "OrderNo2": "",

        "Items": items,

        "Payments": payments,
    }


# ============================================================
# CLOUD SYNC
# ============================================================

def sync_cloud_xml(
    sqlite_db_path,
    cloud_dir,
    target_date=None
):

    if not os.path.exists(
        cloud_dir
    ):

        print(
            f"ERROR: Cloud data folder "
            f"does not exist: {cloud_dir}",
            file=sys.stderr
        )

        return False

    conn = sqlite3.connect(
        sqlite_db_path,
        timeout=30.0
    )

    cursor = conn.cursor()

    try:

        cursor.execute(
            "PRAGMA journal_mode=WAL;"
        )

        ensure_unified_schema(
            cursor
        )

        # ====================================================
        # FIND XML FILES
        # ====================================================

        if target_date:

            date_folder = os.path.join(
                cloud_dir,
                target_date
            )

            alt_date_folder = os.path.join(
                cloud_dir,
                target_date.replace("-", "")
            )

            if os.path.exists(
                date_folder
            ):

                xml_files = find_all_xml_files(
                    date_folder
                )

            elif os.path.exists(
                alt_date_folder
            ):

                xml_files = find_all_xml_files(
                    alt_date_folder
                )

            else:

                xml_files = find_all_xml_files(
                    cloud_dir
                )

            # Remove existing Cloud staging for this date.
            cursor.execute("""
                DELETE FROM StagingItems
                WHERE OrderNo IN (
                    SELECT OrderNo
                    FROM StagingOrders
                    WHERE AcDate = ?
                      AND Source = 'CLOUD'
                )
            """, (target_date,))

            cursor.execute("""
                DELETE FROM StagingPayments
                WHERE OrderNo IN (
                    SELECT OrderNo
                    FROM StagingOrders
                    WHERE AcDate = ?
                      AND Source = 'CLOUD'
                )
            """, (target_date,))

            cursor.execute("""
                DELETE FROM StagingOrders
                WHERE AcDate = ?
                  AND Source = 'CLOUD'
            """, (target_date,))

        else:

            xml_files = find_all_xml_files(
                cloud_dir
            )

            cursor.execute("""
                DELETE FROM StagingItems
                WHERE Source = 'CLOUD'
            """)

            cursor.execute("""
                DELETE FROM StagingPayments
                WHERE Source = 'CLOUD'
            """)

            cursor.execute("""
                DELETE FROM StagingOrders
                WHERE Source = 'CLOUD'
            """)

        # ====================================================
        # VOID ORDERS
        # ====================================================

        voided_order_nos = collect_voided_order_nos(
            xml_files
        )

        orders_synced = 0
        items_synced = 0
        payments_synced = 0
        skipped_non_sale = 0
        skipped_date_mismatch = 0
        errors = 0

        # ====================================================
        # PROCESS XML
        # ====================================================

        for file_path in xml_files:

            if classify_xml_file(
                file_path
            ) != "postorder":
                continue

            try:

                parsed = parse_post_order_file(
                    file_path,
                    voided_order_nos
                )

                if parsed is None:
                    continue

                if parsed == "non_sale":

                    skipped_non_sale += 1
                    continue

                if (
                    target_date
                    and parsed["AcDate"] != target_date
                ):

                    skipped_date_mismatch += 1
                    continue

                # ============================================
                # ORDER
                # ============================================

                cursor.execute("""
                    INSERT INTO StagingOrders (
                        OrderNo,
                        Source,
                        Time,
                        AcDate,
                        NoGuest,
                        Price,
                        Gst,
                        Pst,
                        Disc_amt,
                        Disc_per,
                        Serv,
                        Total,
                        DiscType,
                        Void,
                        Printed,
                        Posted,
                        String1,
                        OrderNo2
                    )
                    VALUES (
                        ?,
                        'CLOUD',
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    ON CONFLICT(OrderNo, Source)
                    DO UPDATE SET
                        Time = excluded.Time,
                        AcDate = excluded.AcDate,
                        NoGuest = excluded.NoGuest,
                        Price = excluded.Price,
                        Gst = excluded.Gst,
                        Pst = excluded.Pst,
                        Disc_amt = excluded.Disc_amt,
                        Disc_per = excluded.Disc_per,
                        Serv = excluded.Serv,
                        Total = excluded.Total,
                        DiscType = excluded.DiscType,
                        Void = excluded.Void,
                        Printed = excluded.Printed,
                        Posted = excluded.Posted,
                        String1 = excluded.String1,
                        OrderNo2 = excluded.OrderNo2,
                        SyncedAt = CURRENT_TIMESTAMP
                """, (
                    parsed["OrderNo"],
                    parsed["Time"],
                    parsed["AcDate"],
                    parsed["NoGuest"],
                    parsed["Price"],
                    parsed["Gst"],
                    parsed["Pst"],
                    parsed["Disc_amt"],
                    parsed["Disc_per"],
                    parsed["Serv"],
                    parsed["Total"],
                    parsed["DiscType"],
                    parsed["Void"],
                    parsed["Printed"],
                    parsed["Posted"],
                    parsed["String1"],
                    parsed["OrderNo2"]
                ))

                orders_synced += 1

                # ============================================
                # ITEMS
                # ============================================

                for item in parsed["Items"]:

                    cursor.execute("""
                        INSERT INTO StagingItems (
                            OrderNo,
                            Source,
                            MenuKey,
                            Status,
                            MenuNo,
                            ItemNo,
                            Description,
                            Qty,
                            Size,
                            PriceBefDisc,
                            DiscValue,
                            Discount,
                            DiscCode,
                            DiscName
                        )
                        VALUES (
                            ?,
                            'CLOUD',
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        )
                    """, (
                        parsed["OrderNo"],
                        item["MenuKey"],
                        item["Status"],
                        item["MenuNo"],
                        item["ItemNo"],
                        item["Description"],
                        item["Qty"],
                        item["Size"],
                        item["PriceBefDisc"],
                        item["DiscValue"],
                        item["Discount"],
                        item["DiscCode"],
                        item["DiscName"]
                    ))

                    items_synced += 1

                # ============================================
                # PAYMENTS
                # ============================================

                for seq_no, payment in enumerate(
                    parsed["Payments"],
                    start=1
                ):

                    pay_name = (
                        payment["PayName"]
                        or ""
                    ).strip()

                    # IMPORTANT:
                    # Register the actual Cloud payment
                    # name, never replace it with OTHERS.
                    ensure_payment_method_exists(
                        cursor,
                        pay_name
                    )

                    cursor.execute("""
                        INSERT INTO StagingPayments (
                            OrderNo,
                            Source,
                            SeqNo,
                            PayID,
                            PayName,
                            Amount,
                            OrgAmount,
                            ExRate,
                            PayDT,
                            Change,
                            PayName2
                        )
                        VALUES (
                            ?,
                            'CLOUD',
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?,
                            ?
                        )
                    """, (
                        parsed["OrderNo"],
                        seq_no,
                        payment["PayID"],
                        pay_name,
                        payment["Amount"],
                        payment["OrgAmount"],
                        payment["ExRate"],
                        payment["PayDT"],
                        payment["Change"],
                        payment["PayName2"]
                    ))

                    payments_synced += 1

            except Exception as ex:

                errors += 1

                print(
                    f"[ERROR] Failed to process "
                    f"'{file_path}': {ex}",
                    file=sys.stderr
                )

        conn.commit()

        print(
            f"SUCCESS: Synced "
            f"{orders_synced} orders, "
            f"{items_synced} items, "
            f"{payments_synced} payments "
            f"to Cloud staging. "
            f"Skipped "
            f"{skipped_non_sale} non-sale entries, "
            f"{skipped_date_mismatch} date mismatches, "
            f"{errors} errors."
        )

        return True

    except Exception as ex:

        conn.rollback()

        print(
            f"ERROR: Cloud sync failed: {ex}",
            file=sys.stderr
        )

        return False

    finally:

        conn.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) >= 3:

        target_date = (
            sys.argv[3]
            if len(sys.argv) >= 4
            else None
        )

        success = sync_cloud_xml(
            sys.argv[1],
            sys.argv[2],
            target_date=target_date
        )

        if not success:
            sys.exit(1)

    else:

        print(
            "Usage: python xml_sync.py "
            "<db_path> "
            "<cloud_data_base_folder> "
            "[target_date YYYY-MM-DD]"
        )