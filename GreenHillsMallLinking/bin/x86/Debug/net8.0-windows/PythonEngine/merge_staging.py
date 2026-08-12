import sqlite3
from collections import defaultdict
from datetime import datetime


# ============================================================
# BASIC HELPERS
# ============================================================

def is_empty(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == ""

    return False


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value):
    return " ".join(clean_text(value).upper().split())


def to_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def choose_value(
    paradox_value,
    cloud_value,
    cloud_preferred=False
):
    """
    Merge two values.

    Rules:
      - both empty       -> empty
      - Paradox empty    -> Cloud
      - Cloud empty      -> Paradox
      - both populated   -> Cloud only wins when cloud_preferred=True
                            otherwise Paradox remains primary
    """

    if is_empty(paradox_value) and is_empty(cloud_value):
        return paradox_value

    if is_empty(paradox_value):
        return cloud_value

    if is_empty(cloud_value):
        return paradox_value

    if cloud_preferred:
        return cloud_value

    return paradox_value


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value):
    """
    Accepts all date formats currently seen in the project.
    """

    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y%m%d",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


# ============================================================
# ITEM MATCHING
# ============================================================

def item_match_score(paradox_item, cloud_item):
    """
    Determine whether two staging rows represent the same
    physical sales item.

    Strong identifiers get higher scores.

    ItemNo       = strongest
    MenuNo       = next
    Description = next
    Qty/Price    = supporting evidence
    """

    score = 0

    p_item = normalize_text(paradox_item.get("ItemNo"))
    c_item = normalize_text(cloud_item.get("ItemNo"))

    p_menu = normalize_text(paradox_item.get("MenuNo"))
    c_menu = normalize_text(cloud_item.get("MenuNo"))

    p_desc = normalize_text(paradox_item.get("Description"))
    c_desc = normalize_text(cloud_item.get("Description"))

    if p_item and c_item and p_item == c_item:
        score += 100

    if p_menu and c_menu and p_menu == c_menu:
        score += 50

    if p_desc and c_desc and p_desc == c_desc:
        score += 30

    p_qty = to_float(paradox_item.get("Qty"))
    c_qty = to_float(cloud_item.get("Qty"))

    if abs(p_qty - c_qty) < 0.0001:
        score += 10

    p_price = to_float(paradox_item.get("PriceBefDisc"))
    c_price = to_float(cloud_item.get("PriceBefDisc"))

    if abs(p_price - c_price) < 0.01:
        score += 10

    return score


def merge_item_rows(paradox_item, cloud_item):
    """
    Combine the two representations of ONE physical item.
    """

    return {
        "MenuKey": choose_value(
            paradox_item.get("MenuKey"),
            cloud_item.get("MenuKey")
        ),

        "Status": choose_value(
            paradox_item.get("Status"),
            cloud_item.get("Status")
        ),

        "MenuNo": choose_value(
            paradox_item.get("MenuNo"),
            cloud_item.get("MenuNo")
        ),

        # Paradox ItemNo is preferred when available.
        "ItemNo": choose_value(
            paradox_item.get("ItemNo"),
            cloud_item.get("ItemNo")
        ),

        # Cloud has better human-readable descriptions.
        "Description": choose_value(
            paradox_item.get("Description"),
            cloud_item.get("Description"),
            cloud_preferred=True
        ),

        "Qty": choose_value(
            paradox_item.get("Qty"),
            cloud_item.get("Qty")
        ),

        "Size": choose_value(
            paradox_item.get("Size"),
            cloud_item.get("Size")
        ),

        "PriceBefDisc": choose_value(
            paradox_item.get("PriceBefDisc"),
            cloud_item.get("PriceBefDisc")
        ),

        "DiscValue": choose_value(
            paradox_item.get("DiscValue"),
            cloud_item.get("DiscValue")
        ),

        "Discount": choose_value(
            paradox_item.get("Discount"),
            cloud_item.get("Discount")
        ),

        "DiscCode": choose_value(
            paradox_item.get("DiscCode"),
            cloud_item.get("DiscCode")
        ),

        "DiscName": choose_value(
            paradox_item.get("DiscName"),
            cloud_item.get("DiscName")
        ),
    }


def merge_items(paradox_items, cloud_items):
    """
    Merge item rows without duplicating the same physical item.

    Matching strategy:

      1. ItemNo
      2. MenuNo
      3. Description
      4. Quantity / price supporting evidence

    Every Cloud row that cannot be matched remains as a
    Cloud-only item.

    Every Paradox row that cannot be matched remains as a
    Paradox-only item.
    """

    remaining_cloud = list(cloud_items)
    merged = []

    for paradox_item in paradox_items:

        best_index = None
        best_score = 0

        for index, cloud_item in enumerate(remaining_cloud):

            score = item_match_score(
                paradox_item,
                cloud_item
            )

            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None and best_score > 0:

            cloud_item = remaining_cloud.pop(best_index)

            merged.append(
                merge_item_rows(
                    paradox_item,
                    cloud_item
                )
            )

        else:
            # Paradox-only item.
            merged.append(dict(paradox_item))

    # Cloud-only items.
    for cloud_item in remaining_cloud:
        merged.append(dict(cloud_item))

    return merged


# ============================================================
# PAYMENT MATCHING
# ============================================================

def payment_match_score(paradox_payment, cloud_payment):

    score = 0

    p_seq = to_int(paradox_payment.get("SeqNo"))
    c_seq = to_int(cloud_payment.get("SeqNo"))

    if p_seq > 0 and c_seq > 0 and p_seq == c_seq:
        score += 100

    p_amount = to_float(paradox_payment.get("Amount"))
    c_amount = to_float(cloud_payment.get("Amount"))

    if abs(p_amount - c_amount) < 0.01:
        score += 50

    p_name = normalize_text(
        paradox_payment.get("PayName")
    )

    c_name = normalize_text(
        cloud_payment.get("PayName")
    )

    if p_name and c_name and p_name == c_name:
        score += 20

    return score


def merge_payment_rows(paradox_payment, cloud_payment):

    return {
        "SeqNo": choose_value(
            paradox_payment.get("SeqNo"),
            cloud_payment.get("SeqNo")
        ),

        "PayID": choose_value(
            paradox_payment.get("PayID"),
            cloud_payment.get("PayID")
        ),

        # IMPORTANT:
        # Cloud PaymentName is authoritative.
        "PayName": choose_value(
            paradox_payment.get("PayName"),
            cloud_payment.get("PayName"),
            cloud_preferred=True
        ),

        "Amount": choose_value(
            paradox_payment.get("Amount"),
            cloud_payment.get("Amount")
        ),

        "OrgAmount": choose_value(
            paradox_payment.get("OrgAmount"),
            cloud_payment.get("OrgAmount")
        ),

        "ExRate": choose_value(
            paradox_payment.get("ExRate"),
            cloud_payment.get("ExRate")
        ),

        "PayDT": choose_value(
            paradox_payment.get("PayDT"),
            cloud_payment.get("PayDT")
        ),

        "Change": choose_value(
            paradox_payment.get("Change"),
            cloud_payment.get("Change")
        ),

        "PayName2": choose_value(
            paradox_payment.get("PayName2"),
            cloud_payment.get("PayName2"),
            cloud_preferred=True
        ),
    }


def merge_payments(paradox_payments, cloud_payments):
    """
    Merge payments without duplicating the same payment.

    Matching:
      1. SeqNo
      2. Amount
      3. PaymentName
    """

    remaining_cloud = list(cloud_payments)
    merged = []

    for paradox_payment in paradox_payments:

        best_index = None
        best_score = 0

        for index, cloud_payment in enumerate(remaining_cloud):

            score = payment_match_score(
                paradox_payment,
                cloud_payment
            )

            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None and best_score > 0:

            cloud_payment = remaining_cloud.pop(
                best_index
            )

            merged.append(
                merge_payment_rows(
                    paradox_payment,
                    cloud_payment
                )
            )

        else:
            merged.append(dict(paradox_payment))

    # Preserve Cloud-only payments.
    for cloud_payment in remaining_cloud:
        merged.append(dict(cloud_payment))

    return merged


# ============================================================
# ORDER MERGING
# ============================================================

def merge_order_rows(paradox_order, cloud_order):

    if paradox_order is None:
        return dict(cloud_order)

    if cloud_order is None:
        return dict(paradox_order)

    return {
        "OrderNo": choose_value(
            paradox_order.get("OrderNo"),
            cloud_order.get("OrderNo")
        ),

        "Time": choose_value(
            paradox_order.get("Time"),
            cloud_order.get("Time"),
            cloud_preferred=True
        ),

        "AcDate": choose_value(
            paradox_order.get("AcDate"),
            cloud_order.get("AcDate"),
            cloud_preferred=True
        ),

        "NoGuest": choose_value(
            paradox_order.get("NoGuest"),
            cloud_order.get("NoGuest")
        ),

        "Price": choose_value(
            paradox_order.get("Price"),
            cloud_order.get("Price")
        ),

        "Gst": choose_value(
            paradox_order.get("Gst"),
            cloud_order.get("Gst")
        ),

        "Pst": choose_value(
            paradox_order.get("Pst"),
            cloud_order.get("Pst")
        ),

        "Disc_amt": choose_value(
            paradox_order.get("Disc_amt"),
            cloud_order.get("Disc_amt")
        ),

        "Disc_per": choose_value(
            paradox_order.get("Disc_per"),
            cloud_order.get("Disc_per")
        ),

        "Serv": choose_value(
            paradox_order.get("Serv"),
            cloud_order.get("Serv")
        ),

        "Total": choose_value(
            paradox_order.get("Total"),
            cloud_order.get("Total")
        ),

        "DiscType": choose_value(
            paradox_order.get("DiscType"),
            cloud_order.get("DiscType"),
            cloud_preferred=True
        ),

        "Void": choose_value(
            paradox_order.get("Void"),
            cloud_order.get("Void")
        ),

        "Printed": choose_value(
            paradox_order.get("Printed"),
            cloud_order.get("Printed")
        ),

        "Posted": choose_value(
            paradox_order.get("Posted"),
            cloud_order.get("Posted")
        ),

        "String1": choose_value(
            paradox_order.get("String1"),
            cloud_order.get("String1")
        ),

        "OrderNo2": choose_value(
            paradox_order.get("OrderNo2"),
            cloud_order.get("OrderNo2")
        ),
    }


# ============================================================
# DATABASE READERS
# ============================================================

ITEM_COLUMNS = [
    "MenuKey",
    "Status",
    "MenuNo",
    "ItemNo",
    "Description",
    "Qty",
    "Size",
    "PriceBefDisc",
    "DiscValue",
    "Discount",
    "DiscCode",
    "DiscName",
]


PAYMENT_COLUMNS = [
    "SeqNo",
    "PayID",
    "PayName",
    "Amount",
    "OrgAmount",
    "ExRate",
    "PayDT",
    "Change",
    "PayName2",
]


def load_items(cursor, order_no, source):

    cursor.execute("""
        SELECT
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
        FROM StagingItems
        WHERE OrderNo = ?
          AND Source = ?
        ORDER BY Id
    """, (order_no, source))

    rows = cursor.fetchall()

    result = []

    for row in rows:
        result.append(
            dict(zip(ITEM_COLUMNS, row))
        )

    return result


def load_payments(cursor, order_no, source):

    cursor.execute("""
        SELECT
            SeqNo,
            PayID,
            PayName,
            Amount,
            OrgAmount,
            ExRate,
            PayDT,
            Change,
            PayName2
        FROM StagingPayments
        WHERE OrderNo = ?
          AND Source = ?
        ORDER BY Id
    """, (order_no, source))

    rows = cursor.fetchall()

    result = []

    for row in rows:
        result.append(
            dict(zip(PAYMENT_COLUMNS, row))
        )

    return result


def load_orders(cursor):

    cursor.execute("""
        SELECT
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
        FROM StagingOrders
        ORDER BY OrderNo, Source
    """)

    rows = cursor.fetchall()

    result = defaultdict(dict)

    for row in rows:

        order = {
            "OrderNo": row[0],
            "Source": row[1],
            "Time": row[2],
            "AcDate": row[3],
            "NoGuest": row[4],
            "Price": row[5],
            "Gst": row[6],
            "Pst": row[7],
            "Disc_amt": row[8],
            "Disc_per": row[9],
            "Serv": row[10],
            "Total": row[11],
            "DiscType": row[12],
            "Void": row[13],
            "Printed": row[14],
            "Posted": row[15],
            "String1": row[16],
            "OrderNo2": row[17],
        }

        result[row[0]][row[1]] = order

    return result


# ============================================================
# PUBLIC MERGE API
# ============================================================

def get_merged_transactions(cursor, target_date_str=None):

    grouped_orders = load_orders(cursor)

    target_date = None

    if target_date_str:
        target_date = parse_date(target_date_str)

    merged_transactions = []

    for order_no, sources in grouped_orders.items():

        paradox = sources.get("PARADOX")
        cloud = sources.get("CLOUD")

        merged = merge_order_rows(
            paradox,
            cloud
        )

        if target_date is not None:

            order_date = parse_date(
                merged.get("AcDate")
            )

            if order_date != target_date:

                # If the merged AcDate didn't resolve cleanly,
                # check either source.
                p_date = parse_date(
                    paradox.get("AcDate")
                    if paradox
                    else None
                )

                c_date = parse_date(
                    cloud.get("AcDate")
                    if cloud
                    else None
                )

                if p_date != target_date and c_date != target_date:
                    continue

        paradox_items = load_items(
            cursor,
            order_no,
            "PARADOX"
        )

        cloud_items = load_items(
            cursor,
            order_no,
            "CLOUD"
        )

        paradox_payments = load_payments(
            cursor,
            order_no,
            "PARADOX"
        )

        cloud_payments = load_payments(
            cursor,
            order_no,
            "CLOUD"
        )

        merged["Items"] = merge_items(
            paradox_items,
            cloud_items
        )

        merged["Payments"] = merge_payments(
            paradox_payments,
            cloud_payments
        )

        merged_transactions.append(merged)

    merged_transactions.sort(
        key=lambda x: str(x.get("OrderNo", ""))
    )

    return merged_transactions


# ============================================================
# OPTIONAL DEBUG FUNCTION
# ============================================================

def print_merge_summary(transactions):

    print("")
    print("=" * 70)
    print("MERGED TRANSACTION SUMMARY")
    print("=" * 70)

    for tx in transactions:

        order_no = tx.get("OrderNo")

        print(
            f"Order {order_no}: "
            f"{len(tx.get('Items', []))} items, "
            f"{len(tx.get('Payments', []))} payments"
        )

        for payment in tx.get("Payments", []):
            print(
                f"  PAYMENT: "
                f"{payment.get('PayName')} "
                f"{to_float(payment.get('Amount')):.2f}"
            )

    print("=" * 70)