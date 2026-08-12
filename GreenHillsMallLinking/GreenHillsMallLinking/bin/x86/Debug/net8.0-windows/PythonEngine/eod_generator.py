import sqlite3
import hashlib
import os
import sys
from datetime import datetime

def log_to_sqlite(db_path, level, message, source="frmProcessEOD"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Logs (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                Timestamp TEXT,
                Level TEXT,
                Message TEXT,
                Source TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO Logs (Timestamp, Level, Message, Source)
            VALUES (?, ?, ?, ?)
        """, (timestamp, level, message, source))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Failed to insert entry into Logs table: {e}", file=sys.stderr)

def format_field(val, length, align='left'):
    val_str = str(val if val is not None else '')
    return val_str.rjust(length)[:length] if align == 'right' else val_str.ljust(length)[:length]

def format_amount(amount, length=17):
    val = float(amount or 0.0)
    return f"{val:.2f}".ljust(length)[:length]

def is_government_discount(disc_type):
    if not disc_type:
        return False
    dt = str(disc_type).strip().upper()
    gov_keywords = ["SENIOR", "PWD", "SOLO", "DIPLOMAT", "DISABILITY", "CITIZEN"]
    return any(keyword in dt for keyword in gov_keywords)

def parse_paradox_time(time_str):
    """Parse Paradox/VB time format '12/30/1899 8:21:38 AM' → 'HH:MM'."""
    if not time_str:
        return ""
    time_str = str(time_str).strip()
    # Paradox zero-date format: 12/30/1899 8:21:38 AM
    try:
        dt = datetime.strptime(time_str, "%m/%d/%Y %I:%M:%S %p")
        return dt.strftime("%H:%M")
    except ValueError:
        pass
    # ISO datetime format: 2026-08-16 08:21:38
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M")
    except ValueError:
        pass
    # Fallback: already a time string
    return time_str[:5] if len(time_str) >= 5 else time_str

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

def generate_eod(db_path, target_date_str, export_folder, source="paradox"):
    source = (source or "paradox").strip().upper()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        ensure_eod_transactions_schema(cursor)

        # 1. Fetch Terminal & Account Configurations
        cursor.execute("SELECT Value FROM Configurations WHERE Key = 'AccountNo'")
        account_row = cursor.fetchone()
        account_no = (account_row[0] if account_row else "00001").zfill(5)

        cursor.execute("SELECT Value FROM Configurations WHERE Key = 'TerminalNo'")
        term_row = cursor.fetchone()
        terminal_no = (term_row[0] if term_row else "0001").zfill(4)

        # 2. Retrieve Orders for Target Date from StagingOrders
        # FIX: Paradox stores AcDate as '08/16/2026 12:00:00 AM' (MM/DD/YYYY),
        # which SQLite's DATE() function cannot parse (returns NULL). We fetch
        # all source rows and filter by date in Python instead.
        cursor.execute("""
            SELECT OrderNo, Time, Total, Gst, Disc_amt, Serv, Void, DiscType, AcDate
            FROM StagingOrders
            WHERE Source = ?
            ORDER BY OrderNo
        """, (source,))
        all_rows = cursor.fetchall()

        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        orders = []
        for row in all_rows:
            ac_date_str = str(row[8]).strip() if row[8] else ""
            row_date = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", 
                        "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
                try:
                    row_date = datetime.strptime(ac_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if row_date == target_dt:
                orders.append(row[:8])   # drop AcDate, keep original 8-column shape

        # 3. Handle Grand Total & Z-Count Trackers
        cursor.execute("""
            SELECT NewGrandTotal, NewZCount FROM GrandTotalTrackers
            WHERE DATE(TargetDate) < DATE(?)
            ORDER BY DATE(TargetDate) DESC LIMIT 1
        """, (target_date_str,))
        last_tracker = cursor.fetchone()
        prev_grand_total = float(last_tracker[0]) if last_tracker and last_tracker[0] else 0.0
        prev_z_count = int(last_tracker[1]) if last_tracker and last_tracker[1] else 0

        cursor.execute("SELECT Id FROM GrandTotalTrackers WHERE DATE(TargetDate) = DATE(?)", (target_date_str,))
        existing_today = cursor.fetchone()

        day_total_sale_amount = 0.0
        day_total_vat = 0.0
        day_total_govt_disc = 0.0
        day_total_promo_disc = 0.0
        day_total_service = 0.0
        day_transaction_count = 0

        for o in orders:
            if str(o[6]).strip() == "1":
                continue

            total_incl_vat = float(o[2] or 0.0)
            vat_amt = float(o[3] or 0.0)
            disc_amt = float(o[4] or 0.0)
            serv_charge = float(o[5] or 0.0)
            disc_type = o[7]

            total_ex_vat = round(total_incl_vat - vat_amt, 2)
            govt_disc = disc_amt if is_government_discount(disc_type) else 0.0
            promo_disc = disc_amt if not is_government_discount(disc_type) else 0.0

            day_total_sale_amount += total_ex_vat
            day_total_vat += vat_amt
            day_total_govt_disc += govt_disc
            day_total_promo_disc += promo_disc
            day_total_service += serv_charge
            day_transaction_count += 1

        total_sales = (day_total_sale_amount + day_total_vat
                        - day_total_promo_disc - day_total_govt_disc + day_total_service)
        refunds = 0.0
        new_grand_total = round(prev_grand_total + total_sales - refunds, 2)
        new_z_count = prev_z_count + 1 if len(orders) > 0 else prev_z_count

        if existing_today:
            cursor.execute("""
                UPDATE GrandTotalTrackers
                SET OldGrandTotal = ?, NewGrandTotal = ?, DayGrossSales = ?,
                    PreviousZCount = ?, NewZCount = ?, CreatedAt = datetime('now')
                WHERE Id = ?
            """, (str(prev_grand_total), str(new_grand_total), str(total_sales),
                  prev_z_count, new_z_count, existing_today[0]))
        else:
            cursor.execute("""
                INSERT INTO GrandTotalTrackers (TargetDate, OldGrandTotal, NewGrandTotal, DayGrossSales, PreviousZCount, NewZCount, CreatedAt)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (target_date_str, str(prev_grand_total), str(new_grand_total), str(total_sales), prev_z_count, new_z_count))

        dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        file_name = f"S{account_no}{terminal_no}{dt.strftime('%m%d%Y')}.SALE"

        if not os.path.exists(export_folder):
            os.makedirs(export_folder)

        full_output_path = os.path.join(export_folder, file_name)

        lines = []
        sales_line_rows = []
        eod_run_id = f"{target_date_str}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute("SELECT Value FROM Configurations WHERE Key = 'PosCode'")
        pos_code_row = cursor.fetchone()
        pos_code = pos_code_row[0] if pos_code_row else ""

        try:
            terminal_no_int = int(terminal_no)
        except (TypeError, ValueError):
            terminal_no_int = 0

        # S Line
        s_line = (
            "S" +
            format_field(account_no, 5) +
            format_field(terminal_no, 4) +
            format_amount(prev_grand_total, 17) +
            format_amount(new_grand_total, 17) +
            format_field(dt.strftime("%m/%d/%Y"), 17)
        )
        lines.append(s_line)
        sales_line_rows.append(("S", "", total_sales, day_total_sale_amount, day_total_vat, new_grand_total, s_line))

        # H and T Lines
        tx_seq = 0
        invoice_seq = 0

        for order in orders:
            real_order_no = str(order[0]).strip()
            invoice_seq += 1
            inv_no = str(invoice_seq)
            time_str = str(order[1]).strip()
            total_incl_vat = float(order[2] or 0.0)
            vat_amt = float(order[3] or 0.0)
            disc_amt = float(order[4] or 0.0)
            serv_charge = float(order[5] or 0.0)
            is_void = "1" if str(order[6]).strip() == "1" else "0"
            disc_type = order[7]

            total_ex_vat = round(total_incl_vat - vat_amt, 2)
            time_hm = parse_paradox_time(time_str)
            dt_formatted = f"{dt.strftime('%m/%d/%Y')} {time_hm}"

            gov_disc = disc_amt if is_government_discount(disc_type) else 0.0
            promo_disc = disc_amt if not is_government_discount(disc_type) else 0.0

            h_line = (
                "H" +
                format_field(inv_no, 14) +
                format_field(dt_formatted, 17) +
                format_amount(total_ex_vat, 17) +
                format_amount(vat_amt, 17) +
                format_amount(gov_disc, 17) +
                format_amount(promo_disc, 17) +
                format_amount(serv_charge, 17) +
                format_field(is_void, 1)
            )
            lines.append(h_line)
            h_net_sales = round(total_ex_vat + vat_amt - gov_disc - promo_disc + serv_charge, 2)
            sales_line_rows.append(("H", time_str, total_incl_vat, total_ex_vat, vat_amt, h_net_sales, h_line))

            cursor.execute("""
                SELECT ItemNo, Description, PriceBefDisc, Qty, DiscValue
                FROM StagingItems
                WHERE OrderNo = ? AND Source = ?
            """, (real_order_no, source))
            items = cursor.fetchall()

            for item in items:
                tx_seq += 1
                item_code = str(item[0]).strip() if item[0] else str(tx_seq)
                desc = str(item[1]).strip() if item[1] else "Item"
                price = float(item[2] or 0.0)
                qty = float(item[3] or 1.0)
                item_disc_value = float(item[4] or 0.0)

                gross_item_total = round(price * qty, 2)
                share_ratio = (gross_item_total / total_incl_vat) if total_incl_vat > 0 else 0.0
                item_vat = round(vat_amt * share_ratio, 2)
                sale_ex_vat = round(gross_item_total - item_vat, 2)

                if is_government_discount(disc_type):
                    item_gov_disc = item_disc_value
                    item_promo_disc = 0.0
                else:
                    item_gov_disc = 0.0
                    item_promo_disc = item_disc_value

                t_line = (
                    "T" +
                    format_field(inv_no, 14) +
                    format_field(tx_seq, 14) +
                    format_field(item_code, 15) +
                    format_field(desc, 50) +
                    format_amount(price, 17) +
                    format_amount(qty, 10) +
                    format_amount(sale_ex_vat, 17) +
                    format_amount(item_vat, 17) +
                    format_amount(item_gov_disc, 17) +
                    format_amount(item_promo_disc, 17)
                )
                lines.append(t_line)
                t_net_sales = round(sale_ex_vat + item_vat - item_gov_disc - item_promo_disc, 2)
                sales_line_rows.append(("T", time_str, gross_item_total, sale_ex_vat, item_vat, t_net_sales, t_line))

        # Checksum & File Write
        content_to_hash = "\r\n".join(lines) + "\r\n"
        md5_hash = hashlib.md5(content_to_hash.encode('utf-8')).hexdigest()
        lines.append(md5_hash)

        with open(full_output_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\r\n".join(lines))

        # FIX: sales_line_rows was being built up through the whole S/H/T loop
        # above (every append() call already existed) but nothing ever actually
        # inserted it anywhere -- this is the missing write.
        try:
            for line_code, sales_time, gross, vatable, vat, net, formatted in sales_line_rows:
                cursor.execute("""
                    INSERT INTO SalesLines (EodRunId, LineCode, SalesTime, PosCode, SalesDate, TerminalNo,
                                            GrossSales, VatableSales, VatAmount, NetSales, FormattedFixedString)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (eod_run_id, line_code, sales_time, pos_code, target_date_str, terminal_no_int,
                      gross, vatable, vat, net, formatted))
        except Exception as sales_line_ex:
            print(f"[WARN] SalesLines insert failed: {sales_line_ex}", file=sys.stderr)

        # EodTransactions UPSERT Logic (Deduplication)
        try:
            store_code_row = cursor.execute("SELECT Value FROM Configurations WHERE Key = 'StoreCode'").fetchone()
            mall_name_row = cursor.execute("SELECT Value FROM Configurations WHERE Key = 'MallName'").fetchone()
            store_code = store_code_row[0] if store_code_row else ""
            mall_name = mall_name_row[0] if mall_name_row else ""

            gross_sales = round(day_total_sale_amount + day_total_vat, 2)
            total_discount = round(day_total_govt_disc + day_total_promo_disc, 2)

            cursor.execute("""
                INSERT INTO EodTransactions (StoreCode, MallName, TransactionDate, GrossSales, NetSales, TotalDiscount, TotalVat, TransactionCount, Status, CreatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Success', datetime('now'))
                ON CONFLICT(TransactionDate) DO UPDATE SET
                    StoreCode=excluded.StoreCode,
                    MallName=excluded.MallName,
                    GrossSales=excluded.GrossSales,
                    NetSales=excluded.NetSales,
                    TotalDiscount=excluded.TotalDiscount,
                    TotalVat=excluded.TotalVat,
                    TransactionCount=excluded.TransactionCount,
                    Status='Success',
                    CreatedAt=datetime('now')
            """, (store_code, mall_name, target_date_str, gross_sales, total_sales, total_discount, day_total_vat, day_transaction_count))

        except Exception as audit_ex:
            print(f"[WARN] EodTransactions upsert write failed: {audit_ex}", file=sys.stderr)

        conn.commit()
        conn.close()

        log_to_sqlite(db_path, "INFO", f"Successfully generated EOD file for {target_date_str}", source="frmProcessEOD")
        print(f"SUCCESS: Generated Greenhills SALE file: {file_name}")
        return True

    except Exception as e:
        err_str = f"EOD Generation failed for {target_date_str}: {str(e)}"
        print(f"ERROR: {err_str}", file=sys.stderr)
        log_to_sqlite(db_path, "ERROR", err_str, source="frmProcessEOD")
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        src = sys.argv[4] if len(sys.argv) >= 5 else "paradox"
        generate_eod(sys.argv[1], sys.argv[2], sys.argv[3], source=src)