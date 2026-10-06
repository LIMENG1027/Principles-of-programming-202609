# Principles-of-programming-202609-LLecture-Assignment 1-2
"""
ITS72604 Principles of Programming - Assessment 1 (Task 4)
Smart Campus EV Charging & Parking Management System - Object-Oriented version

Classes (see the Task 3 UML Class Diagram):
    User            (parent)  - public user, pays the normal rate
    MemberUser      (child)   - IS-A User, staff / student, overrides calculate_fee()
    EVCharger                 - AC / DC charger, owns the Table 1 tariff
    ChargingSession           - HAS-A User and HAS-A EVCharger, produces the bill

OOP concepts demonstrated:
    Inheritance    : MemberUser(User) with super().__init__() and super().calculate_fee()
    Encapsulation  : private attributes (__name) with getters / validating setters
    Polymorphism   : calculate_fee() / get_discount_label() overridden in MemberUser
    Composition    : ChargingSession is built from a User object and an EVCharger object
"""

import math
import re

LINE_WIDTH = 60


# ==========================================================================
# Class 1 : User  (parent class)
# ==========================================================================
class User:
    """A campus EV user who has no staff / student membership (PUBLIC)."""

    def __init__(self, user_id, vehicle_number, is_first_time=False, has_eco_pass=False):
        # Private attributes are initialised through the validating setters
        self.__user_id = None
        self.__vehicle_number = None
        self.__is_first_time = False
        self.__has_eco_pass = False
        self.set_user_id(user_id)
        self.set_vehicle_number(vehicle_number)
        self.set_first_time(is_first_time)
        self.set_eco_pass(has_eco_pass)

    # ---------- getters ----------
    def get_user_id(self):
        return self.__user_id

    def get_vehicle_number(self):
        return self.__vehicle_number

    def is_first_time(self):
        return self.__is_first_time

    def has_eco_pass(self):
        return self.__has_eco_pass

    # ---------- setters with validation ----------
    def set_user_id(self, user_id):
        user_id = str(user_id).strip().upper()
        if not user_id.isalnum():
            raise ValueError(f"Invalid user ID '{user_id}': letters and digits only.")
        self.__user_id = user_id

    def set_vehicle_number(self, vehicle_number):
        plate = str(vehicle_number).strip().upper()
        if not re.fullmatch(r"[A-Z0-9 ]{2,10}", plate):
            raise ValueError(
                f"Invalid vehicle number '{plate}': use 2-10 letters / digits.")
        self.__vehicle_number = plate

    def set_first_time(self, is_first_time):
        if not isinstance(is_first_time, bool):
            raise ValueError("First-time flag must be True or False.")
        self.__is_first_time = is_first_time

    def set_eco_pass(self, has_eco_pass):
        if not isinstance(has_eco_pass, bool):
            raise ValueError("Eco-Pass flag must be True or False.")
        self.__has_eco_pass = has_eco_pass

    # ---------- behaviour (overridden by the child class) ----------
    def get_user_category(self):
        return "PUBLIC"

    def calculate_fee(self, gross_fee, charger_type):
        """Return the charging fee payable after waivers / discounts."""
        if self.__is_first_time:
            return 0.0  # 100% fee waiver for a first-time user
        return gross_fee  # public users pay the normal rate

    def get_discount_label(self, charger_type):
        if self.__is_first_time:
            return "First-Time User Waiver (100%)"
        return "Public Rate (no discount)"

    def __str__(self):
        return f"{self.get_user_category()} user {self.__user_id} [{self.__vehicle_number}]"


# ==========================================================================
# Class 2 : MemberUser  (child class - IS-A User)
# ==========================================================================
class MemberUser(User):
    """A Taylor's STAFF or STUDENT member entitled to a percentage discount."""

    STAFF_DISCOUNT_RATE = 0.50  # all chargers
    STUDENT_DISCOUNT_RATE = 0.25  # AC charger only

    def __init__(self, user_id, vehicle_number, member_type,
                 is_first_time=False, has_eco_pass=False):
        super().__init__(user_id, vehicle_number, is_first_time, has_eco_pass)
        self.__member_type = None
        self.set_member_type(member_type)

    def get_member_type(self):
        return self.__member_type

    def set_member_type(self, member_type):
        member_type = str(member_type).strip().upper()
        if member_type not in ("STAFF", "STUDENT"):
            raise ValueError(f"Invalid member type '{member_type}': STAFF or STUDENT only.")
        self.__member_type = member_type

    def get_user_category(self):  # overriding
        return self.__member_type

    def __discount_rate(self, charger_type):
        """Private helper: percentage discount that applies to this member."""
        if self.__member_type == "STAFF":
            return self.STAFF_DISCOUNT_RATE
        if self.__member_type == "STUDENT" and charger_type == "AC":
            return self.STUDENT_DISCOUNT_RATE
        return 0.0

    def calculate_fee(self, gross_fee, charger_type):  # overriding (polymorphism)
        fee_after_waiver = super().calculate_fee(gross_fee, charger_type)
        if self.is_first_time():  # waiver overrides member discount
            return fee_after_waiver
        return gross_fee * (1 - self.__discount_rate(charger_type))

    def get_discount_label(self, charger_type):  # overriding (polymorphism)
        if self.is_first_time():
            return super().get_discount_label(charger_type)
        rate = self.__discount_rate(charger_type)
        if rate == 0.0:
            return f"{self.__member_type.title()} Discount (AC only) - N/A"
        return f"{self.__member_type.title()} Discount ({rate:.0%})"


# ==========================================================================
# Class 3 : EVCharger
# ==========================================================================
class EVCharger:
    """An AC (7kW) or DC (50kW) charger that owns the Table 1 tariff."""

    # (last hour of tier, AC rate, DC rate)
    TIER_TABLE = [(2, 4.00, 10.00), (4, 6.00, 15.00), (6, 8.00, 20.00)]
    OVERTIME_RATE = {"AC": 12.00, "DC": 30.00}
    MAX_FEE = {"AC": 80.00, "DC": 150.00}
    DESCRIPTION = {"AC": "AC (7kW Fast)", "DC": "DC (50kW Ultra-Fast)"}

    def __init__(self, charger_id, charger_type):
        self.__charger_id = None
        self.__charger_type = None
        self.set_charger_id(charger_id)
        self.set_charger_type(charger_type)

    def get_charger_id(self):
        return self.__charger_id

    def get_charger_type(self):
        return self.__charger_type

    def set_charger_id(self, charger_id):
        charger_id = str(charger_id).strip().upper()
        if not charger_id.replace("-", "").isalnum():
            raise ValueError(f"Invalid charger ID '{charger_id}'.")
        self.__charger_id = charger_id

    def set_charger_type(self, charger_type):
        charger_type = str(charger_type).strip().upper()
        if charger_type not in ("AC", "DC"):
            raise ValueError(f"Invalid charger type '{charger_type}': AC or DC only.")
        self.__charger_type = charger_type

    def get_description(self):
        return self.DESCRIPTION[self.__charger_type]

    def calculate_gross_fee(self, billed_hours):
        """Progressive tiered fee (Table 1), capped at the charger maximum."""
        gross_fee = 0.0
        tier_start = 0
        for tier_end, ac_rate, dc_rate in self.TIER_TABLE:
            hours_in_tier = max(0, min(billed_hours, tier_end) - tier_start)
            rate = ac_rate if self.__charger_type == "AC" else dc_rate
            gross_fee += hours_in_tier * rate
            tier_start = tier_end
        overtime_hours = max(0, billed_hours - tier_start)
        gross_fee += overtime_hours * self.OVERTIME_RATE[self.__charger_type]
        return min(gross_fee, self.MAX_FEE[self.__charger_type])


# ==========================================================================
# Class 4 : ChargingSession  (composed of a User and an EVCharger)
# ==========================================================================
class ChargingSession:
    """One charging visit. HAS-A User and HAS-A EVCharger; generates the bill."""

    ECO_PASS_DISCOUNT = 2.00
    PEAK_SURCHARGE = 5.00
    IDLE_SURCHARGE = 15.00
    CARD_REPLACEMENT_FEE = 30.00
    PEAK_START_HOUR = 12
    PEAK_END_HOUR = 16
    MAX_SESSION_HOURS = 24

    def __init__(self, session_id, user, charger, hours, start_hour,
                 is_idle=False, card_lost=False):
        self.__session_id = None
        self.__user = None
        self.__charger = None
        self.__billed_hours = 0
        self.__start_hour = 0
        self.__is_idle = False
        self.__card_lost = False
        self.set_session_id(session_id)
        self.set_user(user)
        self.set_charger(charger)
        self.set_billed_hours(hours)
        self.set_start_hour(start_hour)
        self.set_idle(is_idle)
        self.set_card_lost(card_lost)

    # ---------- getters ----------
    def get_session_id(self):
        return self.__session_id

    def get_user(self):
        return self.__user

    def get_charger(self):
        return self.__charger

    def get_billed_hours(self):
        return self.__billed_hours

    def get_start_hour(self):
        return self.__start_hour

    def is_idle(self):
        return self.__is_idle

    def is_card_lost(self):
        return self.__card_lost

    # ---------- setters with validation ----------
    def set_session_id(self, session_id):
        if not str(session_id).strip():
            raise ValueError("Session ID cannot be empty.")
        self.__session_id = str(session_id).strip().upper()

    def set_user(self, user):
        if not isinstance(user, User):  # accepts User and MemberUser objects
            raise TypeError("A ChargingSession needs a User object.")
        self.__user = user

    def set_charger(self, charger):
        if not isinstance(charger, EVCharger):
            raise TypeError("A ChargingSession needs an EVCharger object.")
        self.__charger = charger

    def set_billed_hours(self, hours):
        if not isinstance(hours, (int, float)) or isinstance(hours, bool):
            raise ValueError("Hours charged must be a number.")
        if not 0 < hours <= self.MAX_SESSION_HOURS:
            raise ValueError(
                f"Hours must be > 0 and <= {self.MAX_SESSION_HOURS} (got {hours}).")
        self.__billed_hours = math.ceil(hours)  # "per hour or part thereof"

    def set_start_hour(self, start_hour):
        if not isinstance(start_hour, int) or not 0 <= start_hour <= 23:
            raise ValueError(f"Start hour must be a whole number 0-23 (got {start_hour}).")
        self.__start_hour = start_hour

    def set_idle(self, is_idle):
        self.__is_idle = bool(is_idle)

    def set_card_lost(self, card_lost):
        self.__card_lost = bool(card_lost)

    # ---------- business logic ----------
    def is_peak_session(self):
        """True if any billed hour falls between 12 PM and 4 PM."""
        for offset in range(self.__billed_hours):
            current_hour = (self.__start_hour + offset) % 24
            if self.PEAK_START_HOUR <= current_hour < self.PEAK_END_HOUR:
                return True
        return False

    def calculate_bill(self):
        """Return every component of the bill in a dictionary."""
        charger_type = self.__charger.get_charger_type()
        gross_fee = self.__charger.calculate_gross_fee(self.__billed_hours)

        # Polymorphic call: the correct calculate_fee() runs for User or MemberUser
        fee_after_discount = self.__user.calculate_fee(gross_fee, charger_type)
        discount = gross_fee - fee_after_discount

        surcharges = []
        if self.is_peak_session():
            surcharges.append(("Peak Hour Surcharge (12PM-4PM)", self.PEAK_SURCHARGE))
        if self.__is_idle:
            surcharges.append(("Idle Parking Surcharge", self.IDLE_SURCHARGE))
        if self.__card_lost:
            surcharges.append(("Lost RFID Card Replacement", self.CARD_REPLACEMENT_FEE))

        subtotal = fee_after_discount + sum(amount for _, amount in surcharges)
        eco_discount = 0.0
        if self.__user.has_eco_pass():
            eco_discount = min(self.ECO_PASS_DISCOUNT, subtotal)
        return {
            "gross_fee": gross_fee,
            "discount_label": self.__user.get_discount_label(charger_type),
            "discount": discount,
            "fee_after_discount": fee_after_discount,
            "surcharges": surcharges,
            "eco_discount": eco_discount,
            "net_payable": subtotal - eco_discount,
        }

    def generate_bill(self):
        """Print the itemised bill and return the net payable amount."""
        bill = self.calculate_bill()
        double_line, single_line = "=" * LINE_WIDTH, "-" * LINE_WIDTH

        def money_line(description, amount):
            return f"  {description:<44}{amount:>12.2f}"

        print("\n" + double_line)
        print("TAYLOR'S SMART CAMPUS EV CHARGING - OFFICIAL BILL".center(LINE_WIDTH))
        print(double_line)
        print(f"  Session ID   : {self.__session_id}")
        print(f"  User ID      : {self.__user.get_user_id()}")
        print(f"  Vehicle No   : {self.__user.get_vehicle_number()}")
        print(f"  Member Type  : {self.__user.get_user_category()}")
        print(f"  Charger      : {self.__charger.get_charger_id()} - "
              f"{self.__charger.get_description()}")
        print(f"  Duration     : {self.__billed_hours} hour(s) billed "
              f"(start {self.__start_hour:02d}:00)")
        print(single_line)
        print(f"  {'DESCRIPTION':<44}{'AMOUNT (RM)':>12}")
        print(single_line)
        print(money_line("Gross Charging Fee", bill["gross_fee"]))
        print(money_line("Less: " + bill["discount_label"],
                         -bill["discount"] if bill["discount"] else 0.0))
        print(money_line("Charging Fee After Discount", bill["fee_after_discount"]))
        for description, amount in bill["surcharges"]:
            print(money_line("Add : " + description, amount))
        if bill["eco_discount"] > 0:
            print(money_line("Less: Green Eco-Pass Discount", -bill["eco_discount"]))
        print(single_line)
        print(f"  {'NET PAYABLE (RM)':<44}{bill['net_payable']:>12.2f}")
        print(double_line)
        return bill["net_payable"]


# ==========================================================================
# Demonstration program
# ==========================================================================
def print_heading(text):
    print("\n" + "#" * LINE_WIDTH)
    print(f"# {text}")
    print("#" * LINE_WIDTH)


def demo_encapsulation():
    """Part A - private attributes and setter validation."""
    print_heading("PART A : ENCAPSULATION & SETTER VALIDATION")
    user = User("P1000", "ABC 123")
    print("Created  :", user)

    # 1. A private attribute cannot be reached directly from outside the class
    try:
        print(user.__user_id)
    except AttributeError:
        print("Direct access user.__user_id  -> AttributeError (attribute is private)")

    # 2. Valid update through the setter
    user.set_vehicle_number("wqa 9999")
    print("Setter accepted a valid plate  ->", user.get_vehicle_number())

    # 3. Invalid updates are rejected by the setter validation logic
    invalid_updates = [
        ("set_user_id('P-10!')", lambda: user.set_user_id("P-10!")),
        ("set_vehicle_number('#')", lambda: user.set_vehicle_number("#")),
        ("MemberUser member='VISITOR'", lambda: MemberUser("M1", "AB 12", "visitor")),
        ("EVCharger type='XX'", lambda: EVCharger("CH-01", "XX")),
        ("Session hours = -3", lambda: ChargingSession(
            "CS-X", user, EVCharger("CH-01", "AC"), -3, 10)),
    ]
    for label, action in invalid_updates:
        try:
            action()
        except (ValueError, TypeError) as error:
            print(f"Rejected {label:<30}-> {error}")


def demo_polymorphism():
    """Part B - the same call, different behaviour for each object type."""
    print_heading("PART B : POLYMORPHISM - calculate_fee()")
    users = [
        User("P2001", "PUB 001"),
        User("P2002", "NEW 002", is_first_time=True),
        MemberUser("S2003", "STF 003", "staff"),
        MemberUser("S2004", "STU 004", "student"),
        MemberUser("S2005", "STU 005", "student", is_first_time=True),
    ]
    gross_fee = 100.00
    print(f"Gross charging fee = RM {gross_fee:.2f}\n")
    print(f"{'Object':<12}{'Class':<13}{'Charger':<9}{'Fee payable':>12}   Rule applied")
    print("-" * LINE_WIDTH)
    for user in users:
        for charger_type in ("AC", "DC"):
            fee = user.calculate_fee(gross_fee, charger_type)  # polymorphic call
            print(f"{user.get_user_id():<12}{type(user).__name__:<13}{charger_type:<9}"
                  f"{fee:>12.2f}   {user.get_discount_label(charger_type)}")


def demo_billing():
    """Part C - several objects composed into sessions and billed."""
    print_heading("PART C : PROCESSING SIX CHARGING SESSIONS")
    ac_charger = EVCharger("CH-AC-01", "AC")
    dc_charger = EVCharger("CH-DC-01", "DC")

    sessions = [
        ChargingSession("CS-001", MemberUser("S1001", "WXY 1234", "staff"),
                        dc_charger, 8.2, 11),
        ChargingSession("CS-002",
                        MemberUser("S2002", "PKL 8899", "student", has_eco_pass=True),
                        ac_charger, 3, 14, is_idle=True),
        ChargingSession("CS-003", User("P3003", "ABC 55", is_first_time=True),
                        ac_charger, 2, 9, card_lost=True),
        ChargingSession("CS-004", MemberUser("S4004", "VBB 4567", "student"),
                        dc_charger, 4, 8),
        ChargingSession("CS-005", User("P5005", "JQA 7001"),
                        ac_charger, 7, 20),
        ChargingSession("CS-006",
                        User("N6006", "BMK 9090", is_first_time=True, has_eco_pass=True),
                        dc_charger, 1, 12),
    ]

    total_collected = 0.0
    for session in sessions:
        total_collected += session.generate_bill()

    print_heading("SUMMARY")
    print(f"  Sessions processed : {len(sessions)}")
    print(f"  Total collected    : RM {total_collected:.2f}")


def main():
    print("=" * LINE_WIDTH)
    print("SMART CAMPUS EV CHARGING SYSTEM - OBJECT-ORIENTED VERSION".center(LINE_WIDTH))
    print("=" * LINE_WIDTH)
    demo_encapsulation()
    demo_polymorphism()
    demo_billing()


if __name__ == "__main__":
    main()