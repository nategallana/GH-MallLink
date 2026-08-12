import sqlite3
import hashlib
import os
import sys
from datetime import datetime

def format_field(val, length, align='left'):
    val_str = str(val if val is not None else '')
    return val_str.rjust(length)[:length] if align == 'right' else val_str.ljust(length)[:length]

def format_amount(amount, length=17):
    val = float(amount or 0.0)
    return f"{val:.2f}".rjust(length)[:length]

def is_government_discount(disc_type):
    if not disc_type:
        return False
    dt = str(disc_type).strip().upper()
    gov_keywords = ["SENIOR", "PWD", "SOLO", "DIPLOMAT", "DISABILITY", "CITIZEN"]
    return any(keyword in dt for keyword in gov_keywords)

def generate_eod(db_path, target_date_str, export_folder):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Fetch Terminal & Account Configurations
        cursor.execute("SELECT Value FROM Configurations WHERE Key = 'AccountNo'")
        account_row = cursor.fetchone()
        account_no = (account_row[0] if account_row else "00001").zfill(5)

        cursor.execute("SELECT Value FROM Configurations WHERE Key = 'TerminalNo'")
        term_row = cursor.fetchone()
        terminal_no = (term_row[0] if term_row else "0001").zfill(4)

        # 2. Retrieve Orders for Target Date
        cursor.execute("""
            SELECT OrderNo, Time, Total, Gst, Disc_amt, Serv, Void, DiscType
            FROM ParadoxOrders
            WHERE DATE(AcDate) = DATE(?)
        """, (target_date_str,))
        orders = cursor.fetchall()

        # 3. Handle Grand Total & Z-Count Trackers
        cursor.execute("SELECT Id, PreviousZCount, NewZCount FROM GrandTotalTrackers WHERE DATE(TargetDate) = DATE(?)", (target_date_str,))
        existing_today = cursor.fetchone()

        if existing_today:
            cursor.execute("""
                SELECT NewGrandTotal, NewZCount FROM GrandTotalTrackers 
                WHERE DATE(TargetDate) < DATE(?) 
                ORDER BY Id DESC LIMIT 1
            """, (target_date_str,))
            last_tracker = cursor.fetchone()
            prev_grand_total = float(last_tracker[0]) if last_tracker and last_tracker[0] else 0.0
            prev_z_count = int(last_tracker[1]) if last_tracker and last_tracker[1] else 0
        else:
            cursor.execute("SELECT NewGrandTotal, NewZCount FROM GrandTotalTrackers ORDER BY Id DESC LIMIT 1")
            last_tracker = cursor.fetchone()
            prev_grand_total = float(last_tracker[0]) if last_tracker and last_tracker[0] else 0.0
            prev_z_count = int(last_tracker[1]) if last_tracker and last_tracker[1] else 0

        day_net = sum(float(o[2] or 0.0) for o in orders if str(o[6]).strip() != 'Y')
        new_grand_total = prev_grand_total + day_net
        
        # Calculate new Z-Count (increments by 1 each valid run day)
        new_z_count = prev_z_count + 1 if len(orders) > 0 else prev_z_count

        # Upsert GrandTotalTrackers with safe NULL fallbacks
        if existing_today:
            cursor.execute("""
                UPDATE GrandTotalTrackers 
                SET OldGrandTotal = ?, NewGrandTotal = ?, DayGrossSales = ?, 
                    PreviousZCount = ?, NewZCount = ?, CreatedAt = datetime('now')
                WHERE Id = ?
            """, (str(prev_grand_total), str(new_grand_total), str(day_net), prev_z_count, new_z_count, existing_today[0]))
        else:
            cursor.execute("""
                INSERT INTO GrandTotalTrackers (TargetDate, OldGrandTotal, NewGrandTotal, DayGrossSales, PreviousZCount, NewZCount, CreatedAt)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (target_date_str, str(prev_grand_total), str(new_grand_total), str(day_net), prev_z_count, new_z_count))

        # Naming Format: SNNNNNTTTTMMDDYYYY.SALE
        dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        file_name = f"S{account_no}{terminal_no}{dt.strftime('%m%d%Y')}.SALE"

        if not os.path.exists(export_folder):
            os.makedirs(export_folder)

        full_output_path = os.path.join(export_folder, file_name)

        lines = []

        # -------------------------------------------------------------
        # 1. Sale Account Information Record (S)
        # -------------------------------------------------------------
        s_line = (
            "S" +
            format_field(account_no, 5) +
            format_field(terminal_no, 4) +
            format_amount(prev_grand_total, 17) +
            format_amount(new_grand_total, 17) +
            format_field(dt.strftime("%m/%d/%Y"), 17)
        )
        lines.append(s_line)

        # -------------------------------------------------------------
        # 2. Orders & Items Details (H & T Lines)
        # -------------------------------------------------------------
        for order in orders:
            inv_no = str(order[0]).strip()
            time_str = str(order[1]).strip()
            total_amt = float(order[2] or 0.0)
            vat_amt = float(order[3] or 0.0)
            disc_amt = float(order[4] or 0.0)
            serv_charge = float(order[5] or 0.0)
            is_void = "1" if str(order[6]).strip() == "Y" else "0"
            disc_type = order[7]
             
            dt_formatted = f"{dt.strftime('%m/%d/%Y')} {time_str}"

            gov_disc = disc_amt if is_government_discount(disc_type) else 0.0
            promo_disc = disc_amt if not is_government_discount(disc_type) else 0.0

            # Header Line (H)
            h_line = (
                "H" +
                format_field(inv_no, 14) +
                format_field(dt_formatted, 17) +
                format_amount(total_amt, 17) +
                format_amount(vat_amt, 17) +
                format_amount(gov_disc, 17) +
                format_amount(promo_disc, 17) +
                format_amount(serv_charge, 17) +
                format_field(is_void, 1)
            )
            lines.append(h_line)

            # Transaction Line Details (T)
            cursor.execute("""
                SELECT ItemNo, DiscName, PriceBefDisc, Qty, DiscValue, DiscCode
                FROM ParadoxItems 
                WHERE OrderNo = ?
            """, (inv_no,))
            items = cursor.fetchall()

            tx_seq = 1
            for item in items:
                item_code = str(item[0]).strip() if item[0] else str(tx_seq)
                desc = str(item[1]).strip() if item[1] else "Item"
                price = float(item[2] or 0.0)
                qty = float(item[3] or 1.0)
                item_disc = float(item[4] or 0.0)
                item_disc_code = item[5]

                gross_item_total = price * qty

                if is_government_discount(disc_type) or is_government_discount(item_disc_code):
                    sale_ex_vat = gross_item_total
                    item_vat = 0.0
                    item_gov_disc = item_disc
                    item_promo_disc = 0.0
                else:
                    sale_ex_vat = round(gross_item_total / 1.12, 2)
                    item_vat = round(gross_item_total - sale_ex_vat, 2)
                    item_gov_disc = 0.0
                    item_promo_disc = item_disc

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
                tx_seq += 1

        # -------------------------------------------------------------
        # 3. MD5 Checksum Line Generation
        # -------------------------------------------------------------
        content_to_hash = "\r\n".join(lines) + "\r\n"
        md5_hash = hashlib.md5(content_to_hash.encode('utf-8')).hexdigest()
        lines.append(md5_hash)

        # Write to .SALE File
        with open(full_output_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\r\n".join(lines))

        conn.commit()
        conn.close()

        print(f"SUCCESS: Generated Greenhills SALE file: {file_name}")
        return True

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        generate_eod(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python eod_generator.py <db_path> <YYYY-MM-DD> <export_folder>")