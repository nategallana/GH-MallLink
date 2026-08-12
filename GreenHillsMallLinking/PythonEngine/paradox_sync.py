import os
import sqlite3
import sys

try:
    from pypxlib import Table as PxTable
except ImportError:
    print(
        "ERROR: pypxlib module is not installed. "
        "Run 'pip install pypxlib'",
        file=sys.stderr
    )
    sys.exit(1)


DB_PASSWORD = "5A*281"


# ============================================================
# FILE DISCOVERY
# ============================================================

def find_table_file(paradox_dir, base_names):

    if not os.path.exists(paradox_dir):
        return None

    if isinstance(base_names, str):
        base_names = [base_names]

    target_lowers = [
        b.lower()
        for b in base_names
    ]

    for target in target_lowers:

        for file_name in os.listdir(paradox_dir):

            file_base, file_ext = os.path.splitext(
                file_name
            )

            if (
                file_base.lower() == target
                and file_ext.lower() == ".db"
            ):
                return os.path.join(
                    paradox_dir,
                    file_name
                )

    return None


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
        f"Registered payment method: "
        f"'{pay_name_clean}'"
    )


# ============================================================
# VALUE HELPERS
# ============================================================

def get_col_val(row, field_name, default=""):

    try:
        value = row[field_name]

    except Exception:

        try:
            value = getattr(
                row,
                field_name
            )

        except Exception:
            value = None

    if value is None:
        return default

    return str(value).strip()


def get_row_value(row, key, default=""):

    value = row.get(key)

    if value is None:

        for actual_key, actual_value in row.items():

            if actual_key.lower() == key.lower():
                value = actual_value
                break

    if value is None:
        return default

    return str(value).strip()


def number(value, default=0.0):

    try:
        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        return float(text)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# PARADOX FILE SYNC
# ============================================================

def sync_paradox_file(
    sqlite_cursor,
    paradox_dir,
    db_filenames,
    table_type
):

    file_path = find_table_file(
        paradox_dir,
        db_filenames
    )

    if not file_path:

        print(
            f"[WARN] None of the files "
            f"{db_filenames} were found in "
            f"'{paradox_dir}'"
        )

        return 0

    print(
        f"[INFO] Syncing "
        f"{table_type.upper()} "
        f"from file: {file_path}"
    )

    px_table = None

    try:

        px_table = PxTable(
            file_path,
            DB_PASSWORD
        )

    except Exception:

        try:

            px_table = PxTable(
                file_path
            )

        except Exception as ex:

            print(
                f"[ERROR] Could not open "
                f"Paradox file '{file_path}': "
                f"{ex}"
            )

            return 0

    count = 0

    try:

        records = px_table.get_records()

        print(
            f"[INFO] Fast-loaded "
            f"{len(records)} records from "
            f"{table_type.upper()}"
        )

        for row in records:

            order_no = (
                get_row_value(row, "OrderNo")
                or get_row_value(row, "ORDERNO")
                or get_row_value(row, "Order_No")
            )

            if not order_no:
                continue

            # =================================================
            # ORDERS
            # =================================================

            if table_type == "orders":

                pst_val = number(
                    get_row_value(row, "PST")
                    or get_row_value(row, "Pst")
                )

                gst_val = number(
                    get_row_value(row, "GST")
                    or get_row_value(row, "Gst")
                )

                sqlite_cursor.execute("""
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
                        Printed,
                        Posted,
                        Total,
                        Serv,
                        DiscType,
                        Void,
                        String1,
                        OrderNo2
                    )
                    VALUES (
                        ?,
                        'PARADOX',
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
                        Printed = excluded.Printed,
                        Posted = excluded.Posted,
                        Total = excluded.Total,
                        Serv = excluded.Serv,
                        DiscType = excluded.DiscType,
                        Void = excluded.Void,
                        String1 = excluded.String1,
                        OrderNo2 = excluded.OrderNo2,
                        SyncedAt = CURRENT_TIMESTAMP
                """, (
                    order_no,
                    get_row_value(row, "Time"),
                    (
                        get_row_value(row, "AcDate")
                        or get_row_value(row, "Date")
                    ),
                    int(
                        number(
                            get_row_value(
                                row,
                                "NoGuest"
                            )
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "Price"
                        )
                    ),
                    gst_val,
                    pst_val,
                    number(
                        get_row_value(
                            row,
                            "Disc_amt"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "Disc_per"
                        )
                    ),
                    get_row_value(
                        row,
                        "Printed"
                    ),
                    get_row_value(
                        row,
                        "Posted"
                    ),
                    number(
                        get_row_value(
                            row,
                            "Total"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "Serv"
                        )
                    ),
                    get_row_value(
                        row,
                        "DiscType"
                    ),
                    get_row_value(
                        row,
                        "Void",
                        "0"
                    ),
                    get_row_value(
                        row,
                        "String1"
                    ),
                    get_row_value(
                        row,
                        "OrderNo2"
                    )
                ))

                count += 1

            # =================================================
            # ITEMS
            # =================================================

            elif table_type == "items":

                sqlite_cursor.execute("""
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
                        'PARADOX',
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
                    order_no,
                    get_row_value(
                        row,
                        "MenuKey"
                    ),
                    get_row_value(
                        row,
                        "Status"
                    ),
                    get_row_value(
                        row,
                        "MenuNo"
                    ),
                    get_row_value(
                        row,
                        "ItemNo"
                    ),
                    (
                        get_row_value(
                            row,
                            "Description"
                        )
                        or get_row_value(
                            row,
                            "String1"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "Qty"
                        ),
                        1.0
                    ),
                    get_row_value(
                        row,
                        "Size"
                    ),
                    number(
                        get_row_value(
                            row,
                            "PriceBefDisc"
                        )
                        or get_row_value(
                            row,
                            "Price"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "DiscValue"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "Discount"
                        )
                    ),
                    get_row_value(
                        row,
                        "DiscCode"
                    ),
                    get_row_value(
                        row,
                        "DiscName"
                    )
                ))

                count += 1

            # =================================================
            # PAYMENTS
            # =================================================

            elif table_type == "payments":

                pay_name = get_row_value(
                    row,
                    "PayName"
                )

                ensure_payment_method_exists(
                    sqlite_cursor,
                    pay_name
                )

                sqlite_cursor.execute("""
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
                        'PARADOX',
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
                    order_no,
                    int(
                        number(
                            get_row_value(
                                row,
                                "SeqNo"
                            )
                        )
                    ),
                    get_row_value(
                        row,
                        "PayID"
                    ),
                    pay_name,
                    number(
                        get_row_value(
                            row,
                            "Amount"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "OrgAmount"
                        )
                    ),
                    number(
                        get_row_value(
                            row,
                            "ExRate"
                        ),
                        1.0
                    ),
                    get_row_value(
                        row,
                        "PayDT"
                    ),
                    number(
                        get_row_value(
                            row,
                            "Change"
                        )
                    ),
                    get_row_value(
                        row,
                        "PayName2"
                    )
                ))

                count += 1

    except Exception as ex:

        print(
            f"[ERROR] Sync failed for "
            f"{table_type.upper()}: {ex}",
            file=sys.stderr
        )

    finally:

        if px_table:

            try:
                px_table.close()
            except Exception:
                pass

    return count


# ============================================================
# MAIN PARADOX SYNC
# ============================================================

def sync_paradox(
    sqlite_db_path,
    paradox_dir,
    allowed_tables=None,
    password=DB_PASSWORD
):

    conn = sqlite3.connect(
        sqlite_db_path,
        timeout=30
    )

    cursor = conn.cursor()

    try:

        from xml_sync import ensure_unified_schema

        ensure_unified_schema(
            cursor
        )

        # Rebuild only Paradox staging.
        cursor.execute("""
            DELETE FROM StagingItems
            WHERE Source = 'PARADOX'
        """)

        cursor.execute("""
            DELETE FROM StagingPayments
            WHERE Source = 'PARADOX'
        """)

        cursor.execute("""
            DELETE FROM StagingOrders
            WHERE Source = 'PARADOX'
        """)

        orders = sync_paradox_file(
            cursor,
            paradox_dir,
            [
                "ordbkup",
                "orders",
                "order"
            ],
            "orders"
        )

        items = sync_paradox_file(
            cursor,
            paradox_dir,
            [
                "itembkup",
                "items",
                "item"
            ],
            "items"
        )

        payments = sync_paradox_file(
            cursor,
            paradox_dir,
            [
                "ordpaybk",
                "payments",
                "payment"
            ],
            "payments"
        )

        conn.commit()

        print(
            f"SUCCESS: Synced "
            f"{orders} orders, "
            f"{items} items, "
            f"{payments} payments "
            f"from Paradox files."
        )

        return True

    except Exception as ex:

        conn.rollback()

        print(
            f"[ERROR] Paradox sync failed: {ex}",
            file=sys.stderr
        )

        return False

    finally:

        conn.close()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Paradox to SQLite Sync Engine"
    )

    parser.add_argument(
        "--action",
        type=str
    )

    parser.add_argument(
        "--db",
        type=str,
        default="gh_mall_linking.db"
    )

    parser.add_argument(
        "--paradox_dir",
        type=str
    )

    parser.add_argument(
        "--password",
        type=str,
        default=DB_PASSWORD
    )

    args, _ = parser.parse_known_args()

    if args.paradox_dir and args.db:

        success = sync_paradox(
            args.db,
            args.paradox_dir,
            password=args.password
        )

        if not success:
            sys.exit(1)