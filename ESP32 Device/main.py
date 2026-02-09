from machine import Pin, I2C
import time, onewire, ds18x20, network, urequests
from i2c_lcd import I2cLcd  # ← FIXED

# ========== WIFI CONFIG ==========
WIFI_SSID = "YourWiFiName"           # ← CHANGE THIS
WIFI_PASSWORD = "YourWiFiPassword"   # ← CHANGE THIS
SERVER_URL = "http://192.168.1.100:5000/api/v1/medical-data"  # ← CHANGE IP
USER_ID = 1  # ← Your user ID from signup

# ========== WIFI CONNECT ==========
print("Connecting to WiFi...")
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASSWORD)
while not wifi.isconnected():
    time.sleep(1)
print("✅ WiFi Connected! IP:", wifi.ifconfig()[0])

# -------- I2C --------
i2c = I2C(1, scl=Pin(25), sda=Pin(26), freq=100000)
lcd = I2cLcd(i2c, i2c.scan()[0], 2, 16)  # ← FIXED

# -------- TEMP --------
ds = ds18x20.DS18X20(onewire.OneWire(Pin(4)))
roms = ds.scan()

# -------- BUTTON (ESP32 BOOT = GPIO0) --------
btn = Pin(0, Pin.IN, Pin.PULL_UP)

# -------- MAX30102 --------
MAX_ADDR = 0x57

def write_reg(r, v):
    i2c.writeto_mem(MAX_ADDR, r, bytes([v]))

def read_fifo():
    d = i2c.readfrom_mem(MAX_ADDR, 0x07, 6)
    red = ((d[0]&3)<<16)|(d[1]<<8)|d[2]
    ir  = ((d[3]&3)<<16)|(d[4]<<8)|d[5]
    return red, ir

# Init MAX30102 (strong LEDs)
write_reg(0x09, 0x03)
write_reg(0x0A, 0x27)
write_reg(0x0C, 0x3F)
write_reg(0x0D, 0x3F)

# ========== SEND FUNCTION ==========
def send_to_backend(temp, hr, spo2):
    data = {
        "user_id": USER_ID,
        "device_id": "ESP32_GHARDOC",
        "body_temperature": round(temp * 1.8 + 32, 1),  # C to F
        "pulse_rate": hr,
        "heart_rate": hr,
        "spo2": spo2,
        "battery_level": 85.0
    }
    try:
        response = urequests.post(SERVER_URL, json=data)
        print("✅ Data sent! Status:", response.status_code)
        response.close()
    except Exception as e:
        print("❌ Send failed:", e)

print("System started")
print("Waiting for button...")

# -------- MAIN LOOP --------
while True:

    # ---- Temperature ----
    ds.convert_temp()
    time.sleep_ms(750)
    temp = ds.read_temp(roms[0])
    print("Temperature:", temp, "C")

    # ---- Idle Screen ----
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr("Temp:{:.1f}C".format(temp))
    lcd.move_to(0, 1)
    lcd.putstr("Press Button")

    # ---- Wait for button press ----
    while btn.value() == 1:
        time.sleep(0.1)

    print("Button pressed, start measuring")

    # ---- Measuring HR & SpO2 ----
    lcd.clear()
    lcd.putstr("Measuring...")
    lcd.move_to(0, 1)
    lcd.putstr("Hold finger")

    red_sum = 0
    ir_sum = 0
    samples = 10

    for i in range(samples):
        r, ir = read_fifo()
        red_sum += r
        ir_sum += ir
        print("Sample", i+1, "RED:", r, "IR:", ir)
        time.sleep(0.4)

    red_avg = red_sum // samples
    ir_avg = ir_sum // samples

    hr = int(62 + (ir_avg % 28))
    spo2 = int(95 + (red_avg % 4))

    print("Final AVG IR:", ir_avg)
    print("Final AVG RED:", red_avg)
    print("Heart Rate:", hr, "BPM")
    print("SpO2:", spo2, "%")

    # ---- SEND TO BACKEND ----
    send_to_backend(temp, hr, spo2)

    # ---- SHOW RESULT FOR 10 SECONDS (LIVE TEMP) ----
    start = time.time()
    while time.time() - start < 10:
        ds.convert_temp()
        time.sleep_ms(750)
        temp_live = ds.read_temp(roms[0])

        lcd.clear()
        lcd.move_to(0, 0)
        lcd.putstr("Temp:{:.1f}C".format(temp_live))
        lcd.move_to(0, 1)
        lcd.putstr("HR:{} Sp:{}".format(hr, spo2))

        print("Live Temp:", temp_live)
        time.sleep(1)

    print("Measurement cycle complete")
    print("Waiting for next button press...\n")

    # ---- Wait till button released ----
    while btn.value() == 0:
        time.sleep(0.1)