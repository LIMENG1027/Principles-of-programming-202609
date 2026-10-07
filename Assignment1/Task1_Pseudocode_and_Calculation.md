// =====================================================================
// PROGRAM  : Smart Campus EV Charging & Parking Billing System
// PURPOSE  : Calculate the itemised bill of every EV charging session
// =====================================================================
BEGIN EV Charging Billing
 
    // ---------- Constants taken from Table 1 and Table 2 ----------
    DEFINE TIER_LIMIT        = [2, 4, 6]            // last hour of tiers 1, 2，3
    DEFINE AC_RATE           = [4.00, 6.00, 8.00]    // RM per hour, AC 7kW
    DEFINE DC_RATE           = [10.00, 15.00, 20.00] // RM per hour, DC 50kW
    DEFINE AC_OVERTIME_RATE  = 12.00,  AC_MAX_FEE = 80.00
    DEFINE DC_OVERTIME_RATE  = 30.00,  DC_MAX_FEE = 150.00
    DEFINE STAFF_RATE        = 0.50,   STUDENT_RATE = 0.25
    DEFINE ECO_DISCOUNT      = 2.00,   PEAK_SURCHARGE = 5.00
    DEFINE IDLE_SURCHARGE    = 15.00,  CARD_FEE = 30.00
    DEFINE PEAK_START = 12,  PEAK_END = 16          // 12 PM to 4 PM
    DEFINE MAX_HOURS  = 24
 
    SET billCount      = 0
    SET dailyTotal     = 0.00
    SET processAnother = "Y"
 
    // ===== ELEMENT6 : CONTINUOUS PROGRAM LOOP =====
    WHILE processAnother = "Y" DO
 
        // ===== ELEMENT1 : USER INPUT (each field is validated) =====
        REPEAT
            READ userID
        UNTIL userID is not empty AND userID has only letters / digits
 
        REPEAT
            READ vehicleNumber
        UNTIL vehicleNumber has 2 to 10 letters / digits / spaces
 
        DISPLAY "[1] STAFF  [2] STUDENT  [3] PUBLIC"
        REPEAT
            READ memberChoice
        UNTIL memberChoice IN {1, 2, 3}
        SET memberType = STAFF, STUDENT or PUBLIC according to memberChoice
 
        DISPLAY "[1] AC [2] DC"
        REPEAT
            READ chargerChoice
        UNTIL chargerChoice IN {1, 2}
        SET chargerType = "AC" or "DC" according to chargerChoice
 
        REPEAT
            READ hoursCharged
        UNTIL hoursCharged is numeric AND 0 < hoursCharged <= MAX_HOURS
        SET billedHours = CEILING(hoursCharged)     // "per hour or part thereof"
 
        REPEAT
            READ startHour                          // 24-hour clock
        UNTIL startHour is a whole number from 0 to 23
 
        // Special conditions (each answer must be Y or N)
        READ isFirstTime, hasEcoPass, isIdle, cardLost
 
        // ===== ELEMENT2 : CHARGING FEE CALCULATION =====
        SET grossFee = CalculateChargingFee(chargerType, billedHours)
 
        // ===== ELEMENT3 : DISCOUNT AND WAIVER EVALUATION =====
        SET discountAmount = EvaluateDiscount(memberType, chargerType,
                                              isFirstTime, grossFee)
 
        // ===== ELEMENT4 : SURCHARGE AND FEE ADDITION =====
        SET surchargeTotal = 0.00
        IF IsPeakSession(startHour, billedHours) THEN
            SET surchargeTotal = surchargeTotal + PEAK_SURCHARGE
        ENDIF
        IF isIdle = "Y" THEN
            SET surchargeTotal = surchargeTotal + IDLE_SURCHARGE
        ENDIF
        IF cardLost = "Y" THEN
            SET surchargeTotal = surchargeTotal + CARD_FEE
        ENDIF
 
        SET subtotal = grossFee - discountAmount + surchargeTotal
        IF hasEcoPass = "Y" THEN
            SET ecoDiscount = MIN(ECO_DISCOUNT, subtotal)   // never below RM 0.00
        ELSE
            SET ecoDiscount = 0.00
        ENDIF
        SET netPayable = subtotal - ecoDiscount
 
        // ===== ELEMENT5 : FORMATTED BILL OUTPUT =====
        SET billCount  = billCount + 1
        SET dailyTotal = dailyTotal + netPayable
        DISPLAY bill header (bill number, userID, vehicleNumber, memberType,
                             chargerType, billedHours, startHour)
        DISPLAY "Gross Charging Fee"             , grossFee
        DISPLAY "Less: Discount / Waiver"        , -discountAmount
        DISPLAY "Charging Fee After Discount"    , grossFee - discountAmount
        DISPLAY each applicable surcharge        // peak, idle, RFID card
        DISPLAY "Less: Green Eco-Pass Discount"  , -ecoDiscount   // if applicable
        DISPLAY "NET PAYABLE (RM)"               , netPayable
 
        // ===== ELEMENT6 : ASK ATTENDANT TO CONTINUE =====
        REPEAT
            READ processAnother                     // "Y" or "N"
        UNTIL processAnother IN {"Y", "N"}
    ENDWHILE
 
    DISPLAY billCount, dailyTotal                   // end-of-shift summary
END EVChargingBilling
 
 
// ---------------------------------------------------------------------
// FUNCTION1 : progressive tiered fee from Table 1 (capped at the maximum)
// ---------------------------------------------------------------------
FUNCTION CalculateChargingFee(chargerType, billedHours)
    SET grossFee  = 0.00
    SET tierStart = 0
    FOR tier = 1 TO 3 DO                            // tiers: 1-2 h, 3-4 h, 5-6 h
        SET hoursInTier = MAX(0, MIN(billedHours, TIER_LIMIT[tier]) - tierStart)
        IF chargerType = "AC" THEN
            SET hourlyRate = AC_RATE[tier]
        ELSE
            SET hourlyRate = DC_RATE[tier]
        ENDIF
        SET grossFee  = grossFee + hoursInTier * hourlyRate
        SET tierStart = TIER_LIMIT[tier]
    ENDFOR
 
    SET overtimeHours = MAX(0, billedHours - 6)     // hours beyond hour 6
    IF chargerType = "AC" THEN
        SET grossFee = MIN(grossFee + overtimeHours * AC_OVERTIME_RATE, AC_MAX_FEE)
    ELSE
        SET grossFee = MIN(grossFee + overtimeHours * DC_OVERTIME_RATE, DC_MAX_FEE)
    ENDIF
    RETURN grossFee
END FUNCTION
 
 
// ---------------------------------------------------------------------
// FUNCTION2 : member discount / waiver from Table 2 (no stacking of %)
// ---------------------------------------------------------------------
FUNCTION EvaluateDiscount(memberType, chargerType, isFirstTime, grossFee)
    IF isFirstTime = "Y" THEN
        RETURN grossFee                             // 100% waiver overrides others
    ELSE IF memberType = "STAFF" THEN
        RETURN grossFee * STAFF_RATE                // 50%, all chargers
    ELSE IF memberType = "STUDENT" AND chargerType = "AC" THEN
        RETURN grossFee * STUDENT_RATE              // 25%, AC charger only
    ELSE
        RETURN 0.00                                 // public user / student on DC
    ENDIF
END FUNCTION
 
 
// ---------------------------------------------------------------------
// FUNCTION3 : is any billed hour inside the 12 PM - 4 PM peak window?
// ---------------------------------------------------------------------
FUNCTION IsPeakSession(startHour, billedHours)
    FOR offset = 0 TO billedHours - 1 DO
        SET currentHour = (startHour + offset) MOD 24
        IF currentHour >= PEAK_START AND currentHour < PEAK_END THEN
            RETURN TRUE
        ENDIF
    ENDFOR
    RETURN FALSE
END FUNCTION
