# 🚀 QUICK START GUIDE - GHARDOC

## Get Your Backend Running in 5 Minutes!

---

## Step 1: Extract Files

Extract the `gharDoc_backend` folder to your computer.

---

## Step 2: Open Terminal/Command Prompt

**Windows:** Press Win+R, type `cmd`, press Enter

**Mac:** Press Cmd+Space, type `terminal`, press Enter

**Linux:** Press Ctrl+Alt+T

---

## Step 3: Navigate to Backend Folder

```bash
cd path/to/gharDoc_backend
```

Example:
```bash
cd C:\Users\YourName\Desktop\gharDoc_backend
```

---

## Step 4: Create Virtual Environment

```bash
python -m venv venv
```

Wait for it to complete (~30 seconds)

---

## Step 5: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` before your command prompt

---

## Step 6: Install Dependencies

```bash
pip install -r requirements.txt
```

Wait for installation (~2 minutes)

---

## Step 7: Start the Backend!

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

**✅ Backend is running!**

---

## Step 8: Access the Website

Open your browser and go to:
```
http://localhost:5000
```

You should see the GharDoc home page!

---

## Step 9: Create Your Account

1. Click "Sign Up"
2. Fill in your details:
   - Full Name
   - Email
   - Phone (10 digits)
   - Password
3. Click "Create Account"
4. You'll be logged in automatically!

---

## Step 10: Setup ESP32 (Optional for now)

### Find Your Computer's IP Address

**Windows:**
```bash
ipconfig
```
Look for "IPv4 Address" like `192.168.1.100`

**Mac/Linux:**
```bash
ifconfig
```

### Update ESP32 Code

Open `ESP32_GHARDOC_CODE.ino` in Arduino IDE

Change these lines:
```cpp
const char* WIFI_SSID = "Your_WiFi_Name";
const char* WIFI_PASSWORD = "Your_WiFi_Password";
const char* SERVER_URL = "http://192.168.1.100:5000/api/v1/medical-data";
const int USER_ID = 1;  // Your user ID (check dashboard)
```

Upload to ESP32 and open Serial Monitor (115200 baud)

---

## ✅ SUCCESS CHECKLIST

- [ ] Backend running on port 5000
- [ ] Can access http://localhost:5000
- [ ] Created user account
- [ ] Can log in and see dashboard
- [ ] (Optional) ESP32 connected and sending data

---

## 🎯 NEXT STEPS

### Add Your HTML Files

1. Copy your HTML files to `templates/` folder
2. Copy your CSS file to `static/css/` folder
3. Copy your images to `static/images/` folder
4. Update HTML to use Flask syntax (see README.md)

### Test with Simulated Data

Use the test API endpoints to add medical data:

```bash
curl -X POST http://localhost:5000/api/v1/medical-data \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"body_temperature":98.6,"pulse_rate":72,"heart_rate":75,"spo2":98}'
```

Then refresh your dashboard to see the data!

---

## 🐛 COMMON ISSUES

### Issue: "python not recognized"

**Solution:** Install Python from python.org or use `python3` instead of `python`

### Issue: "Cannot find module flask"

**Solution:** 
1. Make sure virtual environment is activated (you see `(venv)`)
2. Run `pip install -r requirements.txt` again

### Issue: "Address already in use"

**Solution:** 
1. Close any program using port 5000
2. Or change port in `app.py`: `app.run(port=5001)`

### Issue: ESP32 can't connect

**Solution:**
1. Make sure ESP32 and computer on same WiFi
2. Check IP address is correct
3. Check firewall isn't blocking Python
4. Backend must be running

---

## 💡 TIPS

1. **Keep terminal open** while using the backend
2. **Press Ctrl+C** in terminal to stop backend
3. **Check logs** in `logs/app.log` if something goes wrong
4. **Use different terminals** for backend and testing
5. **Refresh browser** if pages don't load correctly

---

## 📞 NEED HELP?

Check these files:
- `README.md` - Complete documentation
- `PROJECT_STRUCTURE.md` - File organization
- `logs/app.log` - Error logs

---

## 🎉 That's It!

Your GharDoc backend is now running and ready!

Next: Customize the HTML templates with your content, then test with ESP32!

**Good luck! 🚀**