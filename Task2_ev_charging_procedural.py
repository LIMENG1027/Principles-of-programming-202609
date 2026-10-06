# Principles-of-programming-202609-LLecture-Assignment 1-1
"""
Smart Campus EV Charging & Parking Management System
Procedural prototype: calculates the itemised bill of an EV charging session.

Assumptions (also stated in the Task 1 pseudocode):
  1. Charging time is billed "per hour or part thereof" -> hours are rounded UP.
  2. Table 1 is a progressive (tiered) tariff: hours 1-2, 3-4, 5-6 and 7+ are each
     charged at the rate of their own tier.
  3. The "Max" fee for overtime (AC RM 80 / DC RM 150) caps the TOTAL charging fee.
  4. Discounts / waivers apply to the gross charging fee only. The first-time waiver
     (100%) overrides Staff / Student discounts (no stacking of percentage offers).
  5. Surcharges and the RFID card fee are always payable; the RM 2.00 Eco-Pass
     discount is deducted from the total bill (never below RM 0.00).
  6. The Peak Hour surcharge (12 PM - 4 PM) is charged once if any billed hour of the
     session falls inside the peak window.
"""

import math
import re

# --------------------------------------------------------------------------
# Constants (Table 1 and Table 2)
# --------------------------------------------------------------------------
# (last hour of the tier, AC rate per hour, DC rate per hour)
TIER_TABLE = [
    (2, 4.00, 10.00),  # hours 1 - 2
    (4, 6.00, 15.00),  # hours 3 - 4
    (6, 8.00, 20.00),  # hours 5 - 6
]
OVERTIME_RATE = {"AC": 12.00, "DC": 30.00}  # per hour after hour 6
MAX_CHARGING_FEE = {"AC": 80.00, "DC": 150.00}  # cap on the total charging fee

STAFF_DISCOUNT_RATE = 0.50
STUDENT_DISCOUNT_RATE = 0.25  # AC charger only
ECO_PASS_DISCOUNT = 2.00
PEAK_SURCHARGE = 5.00
IDLE_SURCHARGE = 15.00
CARD_REPLACEMENT_FEE = 30.00

PEAK_START_HOUR = 12  # 12 PM
PEAK_END_HOUR = 16  # 4 PM
MAX_SESSION_HOURS = 24
LINE_WIDTH = 60


# --------------------------------------------------------------------------
# Input functions (Element 1: User Input with validation)
# --------------------------------------------------------------------------
def get_user_id():
    """Ask for a non-empty alphanumeric user ID."""
    while True:
        user_id = input("Enter User ID (e.g. S1001)        : ").strip().upper()
        if user_id.isalnum():
            return user_id
        print("  [!] Invalid ID. Use letters and digits only.")


def get_vehicle_number():
    """Ask for a vehicle plate number (2-10 letters / digits / spaces)."""
    while True:
        plate = input("Enter Vehicle Number (e.g. WXY 1234): ").strip().upper()
        if re.fullmatch(r"[A-Z0-9 ]{2,10}", plate):
            return plate
        print("  [!] Invalid plate number. Use 2-10 letters / digits.")


def get_menu_choice(title, options):
    """Show a numbered menu and return the value chosen by the user."""
    print(title)
    for key, label in options.items():
        print(f"   [{key}] {label}")
    while True:
        choice = input("   Your choice: ").strip()
        if choice in options:
            return options[choice]
        print(f"  [!] Please enter one of: {', '.join(options)}")


def get_hours_charged():
    """Ask for hours charged (0 < hours <= 24) and round up to whole hours."""
    while True:
        text = input(f"Enter hours charged (max {MAX_SESSION_HOURS})        : ").strip()
        try:
            hours = float(text)
        except ValueError:
            print("  [!] Please enter a number, e.g. 2.5")
            continue
        if 0 < hours <= MAX_SESSION_HOURS:
            return math.ceil(hours)  # "per hour or part thereof"
        print(f"  [!] Hours must be greater than 0 and at most {MAX_SESSION_HOURS}.")


def get_start_hour():
    """Ask for the session start hour in 24-hour format (0-23)."""
    while True:
        text = input("Session start hour (0-23, e.g. 13)   : ").strip()
        if text.isdigit() and 0 <= int(text) <= 23:
            return int(text)
        print("  [!] Please enter a whole number from 0 to 23.")


def get_yes_no(question):
    """Return True for yes and False for no."""
    while True:
        answer = input(f"{question} (Y/N): ").strip().upper()
        if answer in ("Y", "N"):
            return answer == "Y"
        print("  [!] Please answer Y or N.")


def read_session_details():
    """Collect every input field of one charging session in a dictionary."""
    print("-" * LINE_WIDTH)
    print("NEW CHARGING SESSION")
    print("-" * LINE_WIDTH)
    session = {
        "user_id": get_user_id(),
        "vehicle_number": get_vehicle_number(),
        "member_type": get_menu_choice(
            "Select Member Type:",
            {"1": "STAFF", "2": "STUDENT", "3": "PUBLIC"}),
        "charger_type": get_menu_choice(
            "Select Charger Type:",
            {"1": "AC", "2": "DC"}),
        "billed_hours": get_hours_charged(),
        "start_hour": get_start_hour(),
    }
    print("Special conditions:")
    session["is_first_time"] = get_yes_no("   First-time user (new registration)?")
    session["has_eco_pass"] = get_yes_no("   Green Eco-Pass holder?             ")
    session["is_idle"] = get_yes_no("   Occupied bay after 100% charge?    ")
    session["card_lost"] = get_yes_no("   Lost RFID access card replacement? ")
    return session


# --------------------------------------------------------------------------
# Calculation functions (Elements 2, 3 and 4)
# --------------------------------------------------------------------------
def calculate_charging_fee(charger_type, billed_hours):
    """Element 2 - progressive tiered fee from Table 1, capped at the maximum."""
    gross_fee = 0.0
    tier_start = 0
    for tier_end, ac_rate, dc_rate in TIER_TABLE:
        hours_in_tier = max(0, min(billed_hours, tier_end) - tier_start)
        hourly_rate = ac_rate if charger_type == "AC" else dc_rate
        gross_fee += hours_in_tier * hourly_rate
        tier_start = tier_end

    overtime_hours = max(0, billed_hours - tier_start)  # hours beyond hour 6
    gross_fee += overtime_hours * OVERTIME_RATE[charger_type]
    return min(gross_fee, MAX_CHARGING_FEE[charger_type])


def evaluate_discount(member_type, charger_type, is_first_time, gross_fee):
    """Element 3 - return (discount_label, discount_amount) from Table 2."""
    if is_first_time:
        return "First-Time User Waiver (100%)", gross_fee
    if member_type == "STAFF":
        return "Staff Discount (50%)", gross_fee * STAFF_DISCOUNT_RATE
    if member_type == "STUDENT" and charger_type == "AC":
        return "Student Discount (25%)", gross_fee * STUDENT_DISCOUNT_RATE
    if member_type == "STUDENT":
        return "Student Discount (AC only) - N/A", 0.0
    return "Member Discount (none)", 0.0


def is_peak_session(start_hour, billed_hours):
    """Return True if any billed hour falls between 12 PM and 4 PM."""
    for hour_offset in range(billed_hours):
        current_hour = (start_hour + hour_offset) % 24
        if PEAK_START_HOUR <= current_hour < PEAK_END_HOUR:
            return True
    return False


def collect_surcharges(session):
    """Element 4 - return a list of (description, amount) surcharge items."""
    surcharges = []
    if is_peak_session(session["start_hour"], session["billed_hours"]):
        surcharges.append(("Peak Hour Surcharge (12PM-4PM)", PEAK_SURCHARGE))
    if session["is_idle"]:
        surcharges.append(("Idle Parking Surcharge", IDLE_SURCHARGE))
    if session["card_lost"]:
        surcharges.append(("Lost RFID Card Replacement", CARD_REPLACEMENT_FEE))
    return surcharges


# --------------------------------------------------------------------------
# Output function (Element 5)
# --------------------------------------------------------------------------
def print_bill(bill_no, session, gross_fee, discount_label, discount_amount,
               surcharges, eco_discount, net_payable):
    """Display the itemised bill."""
    double_line = "=" * LINE_WIDTH
    single_line = "-" * LINE_WIDTH

    def money_line(description, amount):
        return f"  {description:<44}{amount:>12.2f}"

    print("\n" + double_line)
    print("TAYLOR'S SMART CAMPUS EV CHARGING - OFFICIAL BILL".center(LINE_WIDTH))
    print(double_line)
    print(f"  Bill No      : {bill_no:04d}")
    print(f"  User ID      : {session['user_id']}")
    print(f"  Vehicle No   : {session['vehicle_number']}")
    print(f"  Member Type  : {session['member_type']}")
    print(f"  Charger      : {session['charger_type']} "
          f"({'7kW Fast' if session['charger_type'] == 'AC' else '50kW Ultra-Fast'})")
    print(f"  Duration     : {session['billed_hours']} hour(s) billed "
          f"(start {session['start_hour']:02d}:00)")
    print(single_line)
    print(f"  {'DESCRIPTION':<44}{'AMOUNT (RM)':>12}")
    print(single_line)
    print(money_line("Gross Charging Fee", gross_fee))
    print(money_line("Less: " + discount_label,
                     -discount_amount if discount_amount else 0.0))
    print(money_line("Charging Fee After Discount", gross_fee - discount_amount))
    for description, amount in surcharges:
        print(money_line("Add : " + description, amount))
    if eco_discount > 0:
        print(money_line("Less: Green Eco-Pass Discount", -eco_discount))
    print(single_line)
    print(f"  {'NET PAYABLE (RM)':<44}{net_payable:>12.2f}")
    print(double_line)


# --------------------------------------------------------------------------
# Main program (Element 6: continuous loop)
# --------------------------------------------------------------------------
def main():
    """Process charging sessions until the attendant chooses to stop."""
    print("=" * LINE_WIDTH)
    print("SMART CAMPUS EV CHARGING & PARKING MANAGEMENT SYSTEM".center(LINE_WIDTH))
    print("=" * LINE_WIDTH)

    bill_count = 0
    daily_total = 0.0
    process_another = True

    while process_another:
        session = read_session_details()

        # Elements 2 - 4: calculate every component of the bill
        gross_fee = calculate_charging_fee(session["charger_type"],
                                           session["billed_hours"])
        discount_label, discount_amount = evaluate_discount(
            session["member_type"], session["charger_type"],
            session["is_first_time"], gross_fee)
        surcharges = collect_surcharges(session)

        subtotal = gross_fee - discount_amount + sum(amt for _, amt in surcharges)
        eco_discount = min(ECO_PASS_DISCOUNT, subtotal) if session["has_eco_pass"] else 0.0
        net_payable = subtotal - eco_discount

        # Element 5: display the bill
        bill_count += 1
        daily_total += net_payable
        print_bill(bill_count, session, gross_fee, discount_label,
                   discount_amount, surcharges, eco_discount, net_payable)

        # Element 6: ask whether to process another vehicle
        process_another = get_yes_no("\nProcess another vehicle?")

    print("\n" + "=" * LINE_WIDTH)
    print(f"  Vehicles processed : {bill_count}")
    print(f"  Total collected    : RM {daily_total:.2f}")
    print("  Thank you. System closed.")
    print("=" * LINE_WIDTH)


if __name__ == "__main__":
    main()
