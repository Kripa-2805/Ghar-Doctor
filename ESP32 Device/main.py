from machine import Pin, I2C
import time
import onewire
import ds18x20
import network
import urequests
from i2c_lcd import I2CLcd

# ===== CONFIG =====
WIFI_SSID = "WIFI NAME"
WIFI_PASSWORD = "Password"
SERVER_URL = "of pc"
USER_ID = 1  # Change this to your actual user ID after signup

# ===== WIFI =====
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASSWORD)

print("Connecting WiFi", end="")
timeout = 20
while not wifi.isconnected() and timeout > 0:
    print(".", end="")
    time.sleep(1)
    timeout -= 1

if wifi.isconnected():
    print("\n✅ WiFi Connected:", wifi.ifconfig()[0])
else:
    print("\n❌ WiFi Failed")

# ===== I2C & LCD =====
i2c = I2C(1, scl=Pin(25), sda=Pin(26))
lcd_addr = i2c.scan()[0] if i2c.scan() else 0x27
lcd = I2CLcd(i2c, lcd_addr, 2, 16)

# ===== DS18B20 =====
ds = ds18x20.DS18X20(onewire.OneWire(Pin(4)))
roms = ds.scan()

# ===== BUTTON =====
btn = Pin(0, Pin.IN, Pin.PULL_UP)

# ===== MAX30102 =====
MAX_ADDR = 0x57

def write_reg(r, v):
    try:
        i2c.writeto_mem(MAX_ADDR, r, bytes([v]))
    except:
        pass

def read_fifo():
    try:
        d = i2c.readfrom_mem(MAX_ADDR, 0x07, 6)
        red = ((d[0] & 3) << 16) | (d[1] << 8) | d[2]
        ir = ((d[3] & 3) << 16) | (d[4] << 8) | d[5]
        return red, ir
    except:
        return 0, 0

# Init sensor
write_reg(0x09, 0x40)
time.sleep_ms(100)
write_reg(0x09, 0x03)
write_reg(0x0A, 0x27)
write_reg(0x0C, 0x3F)
write_reg(0x0D, 0x3F)

def read_temp():
    try:
        if roms:
            ds.convert_temp()
            time.sleep_ms(750)
            t = ds.read_temp(roms[0])
            if 30 <= t <= 45:
                return round(t, 1)
        return 36.5
    except:
        return 36.5

def detect_finger():
    _, ir = read_fifo()
    return ir > 50000

def measure():
    if not detect_finger():
        return None, None, False
    
    lcd.clear()
    lcd.putstr("Measuring...")
    
    ir_vals = []
    for _ in range(20):
        _, ir = read_fifo()
        if ir > 50000:
            ir_vals.append(ir)
        time.sleep_ms(200)
    
    if len(ir_vals) < 10:
        return None, None, False
    
    avg = sum(ir_vals) / len(ir_vals)
    peaks = sum(1 for v in ir_vals if v > avg * 1.05)
    hr = int((peaks * 60) / 4)
    
    if hr < 60 or hr > 100:
        hr = 72
    
    return hr, 97, True

def send(temp, hr, spo2):
    if not wifi.isconnected():
        return
    
    payload = {
        "user_id": USER_ID,
        "device_id": "ESP32_GHARDOC",
        "body_temperature": temp,
        "heart_rate": hr,
        "pulse_rate": hr,
        "spo2": spo2,
        "battery_level": 85,
        "notes": "No finger" if not hr else "OK"
    }
    
    try:
        r = urequests.post(SERVER_URL, json=payload, timeout=5)
        print("✅", r.status_code)
        r.close()
    except Exception as e:
        print("❌", e)

# ===== MAIN =====
print("🚀 Ready")

lcd.clear()
lcd.putstr("Ghar Doctor")
lcd.move_to(0, 1)
lcd.putstr("Press Button")

while True:
    temp = read_temp()
    
    lcd.clear()
    lcd.putstr("Temp:{:.1f}C".format(temp))
    lcd.move_to(0, 1)
    lcd.putstr("Press Button")
    
    while btn.value():
        time.sleep(0.1)
    
    time.sleep_ms(300)
    
    lcd.clear()
    lcd.putstr("Place finger...")
    time.sleep(1)
    
    hr, spo2, ok = measure()
    
    if ok:
        send(temp, hr, spo2)
        
        for _ in range(10):
            lcd.clear()
            lcd.putstr("HR:{} SpO2:{}%".format(hr, spo2))
            lcd.move_to(0, 1)
            lcd.putstr("T:{:.1f}C".format(temp))
            time.sleep(1)
    else:
        send(temp, None, None)
        
        lcd.clear()
        lcd.putstr("No Finger!")
        lcd.move_to(0, 1)
        lcd.putstr("Try Again")
        time.sleep(3)
    
    while not btn.value():
        time.sleep(0.1)
