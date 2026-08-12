import sqlite3
import hashlib
import os
import sys
from datetime import datetime

from merge_staging import (
    get_merged_transactions,
    parse_date,
)


# ============================================================
# LOGGING
# ============================================================

def log_to_sqlite(
    db_path,
    level,
    message,
    source="frmProcessEOD"
):

    try:

        conn = sqlite3.connect(
            db_path
        )

        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Logs (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp TEXT,
                Level TEXT,
                Message TEXT,
                Source TEXT
            )
        """)

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor.execute("""
            INSERT INTO Logs (
                Timestamp,
                Level,
                Message,
                Source
            )
            VALUES (?, ?, ?, ?)
        """, (
            timestamp,
            level,
            message,
            source
        ))

        conn.commit()
        conn.close()

    except Exception as ex:

        print(
            f"[WARN] Failed to insert "
            f"Logs entry: {ex}",
            file=sys.stderr
        )


# ============================================================
# FORMATTERS
# ============================================================

def format_field(
    value,
    length,
    align="left"
):

    value_string = str(
        value
        if value is not None
        else ""
    )

    if align == "right":

        return value_string.rjust(
            length
        )[:length]

    return value_string.ljust(
        length
    )[:length]


def format_amount(
    amount,
    length=17
):

    try:
        value = float(
            amount or 0.0
        )
    except (
        TypeError,
        ValueError
    ):
        value = 0.0

    return (
        f"{value:.2f}"
        .ljust(length)
        [:length]
    )


def is_government_discount(
    disc_type
):

    if not disc_type:
        return False

    value = str(
        disc_type
    ).strip().upper()

    gov_keywords = [
        "SENIOR",
        "PWD",
        "SOLO",
        "DIPLOMAT",
        "DISABILITY",
        "CITIZEN"
    ]

    return any(
        keyword in value
        for keyword in gov_keywords
    )


def parse_paradox_time(
    time_string
):

    if not time_string:
        return ""

    value = str(
        time_string
    ).strip()

    try:

        parsed = datetime.strptime(
            value,
            "%m/%d/%Y %I:%M:%S %p"
        )

        return parsed.strftime(
            "%H:%M"
        )

    except ValueError:
        pass

    try:

        parsed = datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S"
        )

        return parsed.strftime(
            "%H:%M"
        )

    except ValueError:
        pass

    if len(value) >= 5:
        return value[:5]

    return value


# ============================================================
# EOD TABLE
# ============================================================

def ensure_eod_transactions_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EodTransactions (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            StoreCode TEXT,
            MallName TEXT,
            TransactionDate TEXT UNIQUE,
            GrossSales REAL DEFAULT 0.0,
            NetSales REAL DEFAULT 0.0,
            TotalDiscount REAL DEFAULT 0.0,
            TotalVat REAL DEFAULT 0.0,
            TransactionCount INTEGER DEFAULT 0,
            Status TEXT,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FIX: EF Core may have created this table first without the UNIQUE
    # constraint. This index ensures ON CONFLICT(TransactionDate) works.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS IX_EodTransactions_TransactionDate
        ON EodTransactions(TransactionDate)
    """)


# ============================================================
# GRAND TOTAL TRACKER
# ============================================================

def update_grand_total_tracker(
    cursor,
    target_date_str,
    prev_grand_total,
    new_grand_total,
    total_sales,
    prev_z_count,
    new_z_count
):

    cursor.execute("""
        SELECT Id
        FROM GrandTotalTrackers
        WHERE DATE(TargetDate) = DATE(?)
    """, (
        target_date_str,
    ))

    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
            UPDATE GrandTotalTrackers
            SET
                OldGrandTotal = ?,
                NewGrandTotal = ?,
                DayGrossSales = ?,
                PreviousZCount = ?,
                NewZCount = ?,
                CreatedAt = datetime('now')
            WHERE Id = ?
        """, (
            str(prev_grand_total),
            str(new_grand_total),
            str(total_sales),
            prev_z_count,
            new_z_count,
            existing[0]
        ))

    else:

        cursor.execute("""
            INSERT INTO GrandTotalTrackers (
                TargetDate,
                OldGrandTotal,
                NewGrandTotal,
                DayGrossSales,
                PreviousZCount,
                NewZCount,
                CreatedAt
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                datetime('now')
            )
        """, (
            target_date_str,
            str(prev_grand_total),
            str(new_grand_total),
            str(total_sales),
            prev_z_count,
            new_z_count
        ))


# ============================================================
# EOD GENERATOR
# ============================================================

def generate_eod(
    db_path,
    target_date_str,
    export_folder,
    source="merged"
):

    # Source is intentionally ignored.
    # EOD is ALWAYS generated from the merged
    # Cloud + Paradox representation.
    source = "MERGED"

    conn = None

    try:

        conn = sqlite3.connect(
            db_path,
            timeout=30
        )

        cursor = conn.cursor()

        ensure_eod_transactions_schema(
            cursor
        )

        # ====================================================
        # CONFIGURATION
        # ====================================================

        account_row = cursor.execute("""
            SELECT Value
            FROM Configurations
            WHERE Key = 'AccountNo'
        """).fetchone()

        account_no = (
            account_row[0]
            if account_row
            else "00001"
        )

        account_no = str(
            account_no
        ).zfill(5)

        terminal_row = cursor.execute("""
            SELECT Value
            FROM Configurations
            WHERE Key = 'TerminalNo'
        """).fetchone()

        terminal_no = (
            terminal_row[0]
            if terminal_row
            else "0001"
        )

        terminal_no = str(
            terminal_no
        ).zfill(4)

        pos_code_row = cursor.execute("""
            SELECT Value
            FROM Configurations
            WHERE Key = 'PosCode'
        """).fetchone()

        pos_code = (
            pos_code_row[0]
            if pos_code_row
            else ""
        )

        store_code_row = cursor.execute("""
            SELECT Value
            FROM Configurations
            WHERE Key = 'StoreCode'
        """).fetchone()

        store_code = (
            store_code_row[0]
            if store_code_row
            else ""
        )

        mall_name_row = cursor.execute("""
            SELECT Value
            FROM Configurations
            WHERE Key = 'MallName'
        """).fetchone()

        mall_name = (
            mall_name_row[0]
            if mall_name_row
            else ""
        )

        try:
            terminal_no_int = int(
                terminal_no
            )
        except (
            TypeError,
            ValueError
        ):
            terminal_no_int = 0

        # ====================================================
        # MERGED TRANSACTIONS
        # ====================================================

        orders = get_merged_transactions(
            cursor,
            target_date_str
        )

        # Absolute safety:
        # ONE transaction per OrderNo.
        unique_orders = {}

        for order in orders:

            order_no = str(
                order.get("OrderNo") or ""
            ).strip()

            if not order_no:
                continue

            unique_orders[
                order_no
            ] = order

        orders = list(
            unique_orders.values()
        )

        orders.sort(
            key=lambda x: str(
                x.get("OrderNo", "")
            )
        )

        print(
            f"[INFO] Merged EOD dataset: "
            f"{len(orders)} unique transactions"
        )

        # ====================================================
        # PREVIOUS GRAND TOTAL
        # ====================================================

        cursor.execute("""
            SELECT
                NewGrandTotal,
                NewZCount
            FROM GrandTotalTrackers
            WHERE DATE(TargetDate) < DATE(?)
            ORDER BY DATE(TargetDate) DESC
            LIMIT 1
        """, (
            target_date_str,
        ))

        last_tracker = cursor.fetchone()

        prev_grand_total = (
            float(last_tracker[0])
            if last_tracker
            and last_tracker[0]
            else 0.0
        )

        prev_z_count = (
            int(last_tracker[1])
            if last_tracker
            and last_tracker[1]
            else 0
        )

        # ====================================================
        # DAY TOTALS
        # ====================================================

        day_total_sale_amount = 0.0
        day_total_vat = 0.0
        day_total_govt_disc = 0.0
        day_total_promo_disc = 0.0
        day_total_service = 0.0
        day_transaction_count = 0

        for order in orders:

            if (
                str(
                    order.get("Void") or "0"
                ).strip()
                == "1"
            ):
                continue

            total_incl_vat = float(
                order.get("Total")
                or 0.0
            )

            vat_amt = float(
                order.get("Gst")
                or 0.0
            )

            disc_amt = float(
                order.get("Disc_amt")
                or 0.0
            )

            service_charge = float(
                order.get("Serv")
                or 0.0
            )

            disc_type = order.get(
                "DiscType"
            )

            total_ex_vat = round(
                total_incl_vat - vat_amt,
                2
            )

            if is_government_discount(
                disc_type
            ):

                govt_disc = disc_amt
                promo_disc = 0.0

            else:

                govt_disc = 0.0
                promo_disc = disc_amt

            day_total_sale_amount += (
                total_ex_vat
            )

            day_total_vat += (
                vat_amt
            )

            day_total_govt_disc += (
                govt_disc
            )

            day_total_promo_disc += (
                promo_disc
            )

            day_total_service += (
                service_charge
            )

            day_transaction_count += 1

        # ====================================================
        # TOTALS
        # ====================================================

        total_sales = (
            day_total_sale_amount
            + day_total_vat
            - day_total_promo_disc
            - day_total_govt_disc
            + day_total_service
        )

        refunds = 0.0

        new_grand_total = round(
            prev_grand_total
            + total_sales
            - refunds,
            2
        )

        new_z_count = (
            prev_z_count + 1
            if orders
            else prev_z_count
        )

        # ====================================================
        # TRACKER
        # ====================================================

        update_grand_total_tracker(
            cursor,
            target_date_str,
            prev_grand_total,
            new_grand_total,
            total_sales,
            prev_z_count,
            new_z_count
        )

        # ====================================================
        # FILE NAME
        # ====================================================

        dt = datetime.strptime(
            target_date_str,
            "%Y-%m-%d"
        )

        file_name = (
            f"S"
            f"{account_no}"
            f"{terminal_no}"
            f"{dt.strftime('%m%d%Y')}"
            f".SALE"
        )

        if not os.path.exists(
            export_folder
        ):

            os.makedirs(
                export_folder
            )

        full_output_path = os.path.join(
            export_folder,
            file_name
        )

        lines = []

        sales_line_rows = []

        eod_run_id = (
            f"{target_date_str}_"
            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # ====================================================
        # S LINE
        # ====================================================

        s_line = (
            "S"
            + format_field(
                account_no,
                5
            )
            + format_field(
                terminal_no,
                4
            )
            + format_amount(
                prev_grand_total,
                17
            )
            + format_amount(
                new_grand_total,
                17
            )
            + format_field(
                dt.strftime("%m/%d/%Y"),
                17
            )
        )

        lines.append(
            s_line
        )

        sales_line_rows.append((
            "S",
            "",
            total_sales,
            day_total_sale_amount,
            day_total_vat,
            new_grand_total,
            s_line
        ))

        # ====================================================
        # H + T LINES
        # ====================================================

        tx_seq = 0
        invoice_seq = 0

        for order in orders:

            if (
                str(
                    order.get("Void") or "0"
                ).strip()
                == "1"
            ):
                continue

            real_order_no = str(
                order.get("OrderNo") or ""
            ).strip()

            invoice_seq += 1

            inv_no = str(
                invoice_seq
            )

            time_str = str(
                order.get("Time") or ""
            ).strip()

            total_incl_vat = float(
                order.get("Total")
                or 0.0
            )

            vat_amt = float(
                order.get("Gst")
                or 0.0
            )

            disc_amt = float(
                order.get("Disc_amt")
                or 0.0
            )

            service_charge = float(
                order.get("Serv")
                or 0.0
            )

            disc_type = order.get(
                "DiscType"
            )

            total_ex_vat = round(
                total_incl_vat - vat_amt,
                2
            )

            time_hm = parse_paradox_time(
                time_str
            )

            dt_formatted = (
                f"{dt.strftime('%m/%d/%Y')} "
                f"{time_hm}"
            )

            if is_government_discount(
                disc_type
            ):

                govt_disc = disc_amt
                promo_disc = 0.0

            else:

                govt_disc = 0.0
                promo_disc = disc_amt

            # =================================================
            # H LINE
            # =================================================

            h_line = (
                "H"
                + format_field(
                    inv_no,
                    14
                )
                + format_field(
                    dt_formatted,
                    17
                )
                + format_amount(
                    total_ex_vat,
                    17
                )
                + format_amount(
                    vat_amt,
                    17
                )
                + format_amount(
                    govt_disc,
                    17
                )
                + format_amount(
                    promo_disc,
                    17
                )
                + format_amount(
                    service_charge,
                    17
                )
                + format_field(
                    "0",
                    1
                )
            )

            lines.append(
                h_line
            )

            h_net_sales = round(
                total_ex_vat
                + vat_amt
                - govt_disc
                - promo_disc
                + service_charge,
                2
            )

            sales_line_rows.append((
                "H",
                time_str,
                total_incl_vat,
                total_ex_vat,
                vat_amt,
                h_net_sales,
                h_line
            ))

            # =================================================
            # MERGED ITEMS
            # =================================================

            items = order.get(
                "Items",
                []
            )

            for item in items:

                tx_seq += 1

                item_code = (
                    str(
                        item.get("ItemNo")
                        or ""
                    ).strip()
                    or str(
                        item.get("MenuNo")
                        or ""
                    ).strip()
                    or str(tx_seq)
                )

                description = (
                    str(
                        item.get("Description")
                        or ""
                    ).strip()
                    or "Item"
                )

                price = float(
                    item.get(
                        "PriceBefDisc"
                    )
                    or 0.0
                )

                qty = float(
                    item.get(
                        "Qty"
                    )
                    or 1.0
                )

                item_disc_value = float(
                    item.get(
                        "DiscValue"
                    )
                        or item.get(
                            "Discount"
                        )
                        or 0.0
                )

                gross_item_total = round(
                    price * qty,
                    2
                )

                if total_incl_vat > 0:

                    share_ratio = (
                        gross_item_total
                        / total_incl_vat
                    )

                else:

                    share_ratio = 0.0

                item_vat = round(
                    vat_amt
                    * share_ratio,
                    2
                )

                sale_ex_vat = round(
                    gross_item_total
                    - item_vat,
                    2
                )

                if is_government_discount(
                    disc_type
                ):

                    item_gov_disc = (
                        item_disc_value
                    )

                    item_promo_disc = 0.0

                else:

                    item_gov_disc = 0.0

                    item_promo_disc = (
                        item_disc_value
                    )

                # =============================================
                # T LINE
                # =============================================

                t_line = (
                    "T"
                    + format_field(
                        inv_no,
                        14
                    )
                    + format_field(
                        tx_seq,
                        14
                    )
                    + format_field(
                        item_code,
                        15
                    )
                    + format_field(
                        description,
                        50
                    )
                    + format_amount(
                        price,
                        17
                    )
                    + format_amount(
                        qty,
                        10
                    )
                    + format_amount(
                        sale_ex_vat,
                        17
                    )
                    + format_amount(
                        item_vat,
                        17
                    )
                    + format_amount(
                        item_gov_disc,
                        17
                    )
                    + format_amount(
                        item_promo_disc,
                        17
                    )
                )

                lines.append(
                    t_line
                )

                t_net_sales = round(
                    sale_ex_vat
                    + item_vat
                    - item_gov_disc
                    - item_promo_disc,
                    2
                )

                sales_line_rows.append((
                    "T",
                    time_str,
                    gross_item_total,
                    sale_ex_vat,
                    item_vat,
                    t_net_sales,
                    t_line
                ))

        # ====================================================
        # MD5
        # ====================================================

        content_to_hash = (
            "\r\n".join(lines)
            + "\r\n"
        )

        md5_hash = hashlib.md5(
            content_to_hash.encode(
                "utf-8"
            )
        ).hexdigest()

        lines.append(
            md5_hash
        )

        # ====================================================
        # WRITE SALE FILE
        # ====================================================

        with open(
            full_output_path,
            "w",
            encoding="utf-8",
            newline="\r\n"
        ) as output_file:

            output_file.write(
                "\r\n".join(lines)
            )

        # ====================================================
        # SALES LINES
        # ====================================================

        # Remove previous SalesLines for this date/run
        # only if your schema permits it.
        #
        # We intentionally insert the exact same S/H/T
        # records that were written to the SALE file.

        try:

            for (
                line_code,
                sales_time,
                gross,
                vatable,
                vat,
                net,
                formatted
            ) in sales_line_rows:

                cursor.execute("""
                    INSERT INTO SalesLines (
                        EodRunId,
                        LineCode,
                        SalesTime,
                        PosCode,
                        SalesDate,
                        TerminalNo,
                        GrossSales,
                        VatableSales,
                        VatAmount,
                        NetSales,
                        FormattedFixedString
                    )
                    VALUES (
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
                    eod_run_id,
                    line_code,
                    sales_time,
                    pos_code,
                    target_date_str,
                    terminal_no_int,
                    gross,
                    vatable,
                    vat,
                    net,
                    formatted
                ))

        except Exception as sales_line_ex:

            raise RuntimeError(
                "SalesLines insert failed: "
                f"{sales_line_ex}"
            ) from sales_line_ex

        # ====================================================
        # EOD TRANSACTION
        # ====================================================

        gross_sales = round(
            day_total_sale_amount
            + day_total_vat,
            2
        )

        total_discount = round(
            day_total_govt_disc
            + day_total_promo_disc,
            2
        )

        cursor.execute("""
            INSERT INTO EodTransactions (
                StoreCode,
                MallName,
                TransactionDate,
                GrossSales,
                NetSales,
                TotalDiscount,
                TotalVat,
                TransactionCount,
                Status,
                CreatedAt
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                'Success',
                datetime('now')
            )
            ON CONFLICT(TransactionDate)
            DO UPDATE SET
                StoreCode = excluded.StoreCode,
                MallName = excluded.MallName,
                GrossSales = excluded.GrossSales,
                NetSales = excluded.NetSales,
                TotalDiscount = excluded.TotalDiscount,
                TotalVat = excluded.TotalVat,
                TransactionCount = excluded.TransactionCount,
                Status = 'Success',
                CreatedAt = datetime('now')
        """, (
            store_code,
            mall_name,
            target_date_str,
            gross_sales,
            total_sales,
            total_discount,
            day_total_vat,
            day_transaction_count
        ))

        conn.commit()

        conn.close()
        conn = None

        log_to_sqlite(
            db_path,
            "INFO",
            (
                f"Successfully generated "
                f"MERGED EOD file for "
                f"{target_date_str}. "
                f"Transactions={day_transaction_count}"
            ),
            source="frmProcessEOD"
        )

        print(
            f"SUCCESS: Generated merged "
            f"Greenhills SALE file: "
            f"{file_name}"
        )

        return True

    except Exception as ex:

        if conn:

            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass

        error_string = (
            f"EOD Generation failed "
            f"for {target_date_str}: "
            f"{ex}"
        )

        print(
            f"ERROR: {error_string}",
            file=sys.stderr
        )

        log_to_sqlite(
            db_path,
            "ERROR",
            error_string,
            source="frmProcessEOD"
        )

        return False


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) >= 4:

        # The fourth argument is accepted for backwards
        # compatibility, but MERGED is always used.
        requested_source = (
            sys.argv[4]
            if len(sys.argv) >= 5
            else "merged"
        )

        generate_eod(
            sys.argv[1],
            sys.argv[2],
            sys.argv[3],
            source="merged"
        )

    else:

        print(
            "Usage: python eod_generator.py "
            "<db_path> "
            "<target_date YYYY-MM-DD> "
            "<export_folder> "
            "[source]"
        )