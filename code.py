import time  # Library for delay and timing
import board  # Library for Raspberry Pi Pico pins
import digitalio  # Library for digital input and output
import busio  # Library for I2C communication
import lcd  # LCD screen library
import i2c_pcf8574_interface  # I2C interface library for LCD

# =========================================================
# LCD SETUP
# =========================================================

i2c = busio.I2C(scl=board.GP27, sda=board.GP26)  # Create I2C connection

i2c_interface = i2c_pcf8574_interface.I2CPCF8574Interface(i2c, 0x27)  # LCD I2C address

display = lcd.LCD(i2c_interface, num_rows=2, num_cols=16)  # Create LCD object

display.set_backlight(True)  # Turn on LCD light
display.set_display_enabled(True)  # Enable LCD display

# =========================================================
# 7 SEGMENT SETUP (CD4511)
# =========================================================

# BCD pins A B C D
bcd_pins = [board.GP6, board.GP7, board.GP8, board.GP9]  # BCD output pins

class CD4511:  # Class for CD4511 decoder

    def __init__(self, pins):  # Initialize function

        self.bcd = []  # Empty list for pins

        for pin in pins:  # Loop through pins

            p = digitalio.DigitalInOut(pin)  # Create digital pin
            p.direction = digitalio.Direction.OUTPUT  # Set as output

            self.bcd.append(p)  # Add pin to list

    def send_bcd(self, value):  # Send number to 7 segment

        value = max(0, min(9, value))  # Limit number from 0 to 9

        for i in range(4):  # Loop through 4 bits

            self.bcd[i].value = (value >> i) & 1  # Send bit value

segment = CD4511(bcd_pins)  # Create CD4511 object

# =========================================================
# LATCH PINS
# =========================================================

# S71 = ONES
# S72 = TENS

s71 = digitalio.DigitalInOut(board.GP15)  # Ones digit latch
s72 = digitalio.DigitalInOut(board.GP16)  # Tens digit latch

s71.direction = digitalio.Direction.OUTPUT  # Set as output
s72.direction = digitalio.Direction.OUTPUT  # Set as output

s71.value = True  # Default HIGH
s72.value = True  # Default HIGH

# =========================================================
# KEYPAD SETUP (MM74C922)
# =========================================================

# DATA AVAILABLE
data_available = digitalio.DigitalInOut(board.GP14)  # Data available pin
data_available.direction = digitalio.Direction.INPUT  # Set as input

# D0 D1 D2 D3
data_pins = [
    board.GP13,
    board.GP12,
    board.GP11,
    board.GP10
]

data_inputs = []  # Empty list for keypad inputs

for pin in data_pins:  # Loop through keypad pins

    dio = digitalio.DigitalInOut(pin)  # Create digital pin
    dio.direction = digitalio.Direction.INPUT  # Set as input

    data_inputs.append(dio)  # Add pin to list

# =========================================================
# KEYPAD MAP
# =========================================================

keypad_map = {
    12: '1', 13: '2', 14: '3', 15: 'A',
    8: '4', 9: '5', 10: '6', 11: 'B',
    4: '7', 5: '8', 6: '9', 7: 'C',
    0: '*', 1: '0', 2: '#', 3: 'D'
}  # Keypad buttons map

# =========================================================
# PARKING LEDS
# =========================================================

slot1_led = digitalio.DigitalInOut(board.GP2)  # Slot 1 LED
slot1_led.direction = digitalio.Direction.OUTPUT  # Set as output

slot2_led = digitalio.DigitalInOut(board.GP3)  # Slot 2 LED
slot2_led.direction = digitalio.Direction.OUTPUT  # Set as output

slot3_led = digitalio.DigitalInOut(board.GP4)  # Slot 3 LED
slot3_led.direction = digitalio.Direction.OUTPUT  # Set as output

# =========================================================
# STATUS LEDS
# =========================================================

green_led = digitalio.DigitalInOut(board.GP18)  # Green LED
green_led.direction = digitalio.Direction.OUTPUT  # Set as output

red_led = digitalio.DigitalInOut(board.GP19)  # Red LED
red_led.direction = digitalio.Direction.OUTPUT  # Set as output

# =========================================================
# ENTRY / EXIT LAMPS
# =========================================================

entry_lamp = digitalio.DigitalInOut(board.GP21)  # Entry lamp
entry_lamp.direction = digitalio.Direction.OUTPUT  # Set as output

exit_lamp = digitalio.DigitalInOut(board.GP0)  # Exit lamp
exit_lamp.direction = digitalio.Direction.OUTPUT  # Set as output

# =========================================================
# ALARM LED
# =========================================================

alarm_led = digitalio.DigitalInOut(board.GP20)  # Alarm LED
alarm_led.direction = digitalio.Direction.OUTPUT  # Set as output

# =========================================================
# BUTTONS
# =========================================================

exit_button = digitalio.DigitalInOut(board.GP22)  # Exit button
exit_button.direction = digitalio.Direction.INPUT  # Set as input
exit_button.pull = digitalio.Pull.UP  # Enable pull-up resistor

alarm_button = digitalio.DigitalInOut(board.GP28)  # Alarm button
alarm_button.direction = digitalio.Direction.INPUT  # Set as input
alarm_button.pull = digitalio.Pull.UP  # Enable pull-up resistor

# =========================================================
# VARIABLES
# =========================================================

password = "0571"  # System password

user_input = ""  # User entered password

attempts = 3  # Number of password tries

system_open = False  # Parking state

TOTAL_SLOTS = 3  # Total parking slots

occupied_slots = 0  # Number of occupied slots

parking_slots = [0, 0, 0]  # Slot status list

# =========================================================
# 7 SEGMENT DISPLAY FUNCTION
# =========================================================

def update_display():  # Function to update 7 segment display

    available = TOTAL_SLOTS - occupied_slots  # Calculate free slots

    tens = available // 10  # Tens digit
    ones = available % 10  # Ones digit

    # TENS DISPLAY
    segment.send_bcd(tens)  # Send tens digit

    s72.value = False  # Activate tens latch
    time.sleep(0.001)  # Small delay
    s72.value = True  # Disable tens latch

    # ONES DISPLAY
    segment.send_bcd(ones)  # Send ones digit

    s71.value = False  # Activate ones latch
    time.sleep(0.001)  # Small delay
    s71.value = True  # Disable ones latch

# =========================================================
# LCD FUNCTIONS
# =========================================================

def show_slots():  # Show parking slots status

    line = ""  # Empty line

    for i in range(3):  # Loop through slots

        if parking_slots[i] == 0:  # If slot is free

            line += "S" + str(i + 1) + ":F "  # Add free status

        else:  # If slot is occupied

            line += "S" + str(i + 1) + ":O "  # Add occupied status

    display.clear()  # Clear LCD

    display.set_cursor_pos(0, 0)  # First row
    display.print("SMART PARKING")  # Print title

    display.set_cursor_pos(1, 0)  # Second row
    display.print(line[:16])  # Print slots status

def show_message(line1, line2):  # Show message on LCD

    display.clear()  # Clear LCD

    display.set_cursor_pos(0, 0)  # First row
    display.print(line1)  # Print first line

    display.set_cursor_pos(1, 0)  # Second row
    display.print(line2)  # Print second line

# =========================================================
# LED FUNCTION
# =========================================================

def update_leds():  # Update LEDs status

    slot1_led.value = parking_slots[0]  # Slot 1 LED state
    slot2_led.value = parking_slots[1]  # Slot 2 LED state
    slot3_led.value = parking_slots[2]  # Slot 3 LED state

    if occupied_slots < TOTAL_SLOTS:  # If parking not full

        green_led.value = True  # Green ON
        red_led.value = False  # Red OFF

    else:  # If parking full

        green_led.value = False  # Green OFF
        red_led.value = True  # Red ON

# =========================================================
# KEYPAD FUNCTION
# =========================================================

def read_key():  # Read keypad button

    if data_available.value:  # If key pressed

        value = 0  # Start value

        for i, pin in enumerate(data_inputs):  # Read keypad bits

            if pin.value:  # If bit is HIGH

                value |= (1 << (3 - i))  # Build binary value

        while data_available.value:  # Wait until key release
            pass

        return keypad_map.get(value, '?')  # Return keypad value

    return None  # No key pressed

# =========================================================
# ENTRY LIGHT FUNCTION
# =========================================================

def entry_open():  # Open entry gate

    entry_lamp.value = True  # Turn on entry lamp
    alarm_led.value = True  # Turn on alarm LED

    time.sleep(0.3)  # Delay

    alarm_led.value = False  # Turn off alarm LED

    time.sleep(3)  # Keep gate open

    entry_lamp.value = False  # Turn off entry lamp

# =========================================================
# EXIT LIGHT FUNCTION
# =========================================================

def exit_open():  # Open exit gate

    exit_lamp.value = True  # Turn on exit lamp
    alarm_led.value = True  # Turn on alarm LED

    time.sleep(0.3)  # Delay

    alarm_led.value = False  # Turn off alarm LED

    time.sleep(3)  # Keep gate open

    exit_lamp.value = False  # Turn off exit lamp

# =========================================================
# STARTUP
# =========================================================

entry_lamp.value = False  # Entry lamp OFF
exit_lamp.value = False  # Exit lamp OFF

update_display()  # Update display
update_leds()  # Update LEDs

show_message("PARKING LOCKED", "ENTER PASSWORD")  # Startup message

# =========================================================
# MAIN LOOP
# =========================================================

while True:  # Infinite loop

    update_display()  # Refresh display
    update_leds()  # Refresh LEDs

    key = read_key()  # Read keypad input

    # =====================================================
    # PASSWORD SYSTEM
    # =====================================================

    if system_open == False:  # If system locked

        if key:  # If key pressed

            if key == "#":  # Confirm button

                if user_input == password:  # Correct password

                    system_open = True  # Open system

                    attempts = 3  # Reset attempts

                    user_input = ""  # Clear input

                    show_message("ACCESS GRANTED", "PARKING OPEN")  # Success message

                    green_led.value = True  # Green LED ON
                    alarm_led.value = True  # Alarm LED ON

                    time.sleep(1)  # Delay

                    alarm_led.value = False  # Alarm LED OFF

                    show_slots()  # Show slots

                else:  # Wrong password

                    attempts -= 1  # Reduce attempts

                    show_message("WRONG PASSWORD", "TRY AGAIN")  # Error message

                    red_led.value = True  # Red LED ON
                    alarm_led.value = True  # Alarm LED ON

                    time.sleep(1)  # Delay

                    red_led.value = False  # Red LED OFF
                    alarm_led.value = False  # Alarm LED OFF

                    if attempts == 0:  # If no attempts left

                        show_message("SYSTEM LOCKED", "WAIT 10 SEC")  # Lock message

                        for seconds in range(10, -1, -1):  # Countdown loop

                            segment.send_bcd(seconds % 10)  # Show countdown

                            s71.value = False  # Activate latch
                            time.sleep(0.001)  # Small delay
                            s71.value = True  # Disable latch

                            red_led.value = True  # Red LED ON
                            green_led.value = True  # Green LED ON

                            slot1_led.value = True  # Slot 1 LED ON
                            slot2_led.value = True  # Slot 2 LED ON
                            slot3_led.value = True  # Slot 3 LED ON

                            alarm_led.value = True  # Alarm LED ON

                            time.sleep(0.5)  # Delay

                            red_led.value = False  # Red LED OFF
                            green_led.value = False  # Green LED OFF

                            slot1_led.value = False  # Slot 1 LED OFF
                            slot2_led.value = False  # Slot 2 LED OFF
                            slot3_led.value = False  # Slot 3 LED OFF

                            alarm_led.value = False  # Alarm LED OFF

                            time.sleep(0.5)  # Delay

                        attempts = 3  # Reset attempts

                    user_input = ""  # Clear input

                    show_message("PARKING LOCKED", "ENTER PASSWORD")  # Lock message

            elif key == "*":  # Delete button

                user_input = user_input[:-1]  # Remove last digit

            elif len(user_input) < 4:  # Limit password length

                if key.isdigit():  # Accept numbers only

                    user_input += key  # Add digit

            if system_open == False:  # If still locked

                display.set_cursor_pos(1, 0)  # Second row
                display.print("                ")  # Clear row

                display.set_cursor_pos(1, 0)  # Second row
                display.print("*" * len(user_input))  # Show hidden password

    # =====================================================
    # PARKING SYSTEM
    # =====================================================

    else:  # If system open

        # =================================================
        # EXIT BUTTON
        # =================================================

        if not exit_button.value:  # If exit button pressed

            show_message("CAR EXITED", "EXIT OPENING")  # Exit message

            exit_open()  # Open exit gate

            occupied_slots = max(0, occupied_slots - 1)  # Reduce occupied slots

            for i in range(3):  # Loop through slots

                if parking_slots[i] == 1:  # Find occupied slot

                    parking_slots[i] = 0  # Free slot
                    break  # Exit loop

            update_leds()  # Update LEDs

            show_slots()  # Show slot status

            time.sleep(1)  # Delay

        # =================================================
        # ALARM BUTTON
        # =================================================

        if not alarm_button.value:  # If alarm button pressed

            show_message("EMERGENCY!", "ALARM ACTIVE")  # Alarm message

            for i in range(15):  # Alarm flashing loop

                red_led.value = True  # Red LED ON
                green_led.value = True  # Green LED ON

                slot1_led.value = True  # Slot 1 LED ON
                slot2_led.value = True  # Slot 2 LED ON
                slot3_led.value = True  # Slot 3 LED ON

                alarm_led.value = True  # Alarm LED ON

                time.sleep(0.15)  # Delay

                red_led.value = False  # Red LED OFF
                green_led.value = False  # Green LED OFF

                slot1_led.value = False  # Slot 1 LED OFF
                slot2_led.value = False  # Slot 2 LED OFF
                slot3_led.value = False  # Slot 3 LED OFF

                alarm_led.value = False  # Alarm LED OFF

                time.sleep(0.15)  # Delay

            update_leds()  # Update LEDs

            show_slots()  # Show slots

        # =================================================
        # SLOT SELECTION
        # =================================================

        if key in ["1", "2", "3"]:  # If slot selected

            slot = int(key) - 1  # Convert slot number

            if parking_slots[slot] == 0:  # If slot free

                show_message("SLOT " + key + " FREE", "ENTRY OPENING")  # Free message

                entry_open()  # Open entry gate

                parking_slots[slot] = 1  # Mark slot occupied

                occupied_slots += 1  # Increase occupied count

            else:  # If slot busy

                show_message("SLOT " + key + " BUSY", "CHOOSE ANOTHER")  # Busy message

                time.sleep(1)  # Delay

            update_leds()  # Update LEDs

            show_slots()  # Show slots

    time.sleep(0.1)  # Small loop delay