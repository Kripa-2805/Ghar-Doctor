/*
 * GharDoc ESP32 Code
 * Rural Healthcare Monitoring Device
 * 
 * Features:
 * - Measures body temperature, pulse rate, heart rate, SpO2
 * - Stores up to 200 readings in memory when offline
 * - Batch uploads when connection restored
 * - Low power consumption for rural areas
 * 
 * Author: Your Name
 * Date: February 2026
 * Version: 1.0.0
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==================== CONFIGURATION ====================

// WiFi Credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";        // Change this
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"; // Change this

// Backend Server Configuration
const char* SERVER_URL = "http://192.168.1.100:5000/api/v1/medical-data";  // Change IP
const char* BATCH_URL = "http://192.168.1.100:5000/api/v1/medical-data/batch";
const int USER_ID = 1;  // Change to your user ID after registration
const char* DEVICE_ID = "ESP32_GHARDOC_001";  // Unique device ID

// Sensor Pins
#define TEMP_SENSOR_PIN 34  // Temperature sensor (analog)
#define PULSE_SENSOR_PIN 35  // Pulse sensor (analog)
#define SPO2_SENSOR_PIN 32  // SpO2 sensor (analog)

// Timing Configuration
const unsigned long READING_INTERVAL = 300000;  // Take reading every 5 minutes (300000 ms)
const unsigned long SEND_INTERVAL = 30000;      // Try to send every 30 seconds when online
const unsigned long WIFI_RETRY_INTERVAL = 60000; // Retry WiFi connection every minute

// Memory Buffer Configuration
const int MAX_BUFFER_SIZE = 200;  // Store up to 200 readings offline
const int BATCH_SEND_SIZE = 20;   // Send 20 readings per batch

// ==================== DATA STRUCTURES ====================

struct MedicalReading {
    float bodyTemperature;  // °F
    int pulseRate;          // bpm
    int heartRate;          // bpm
    float spo2;             // %
    unsigned long recordedAt; // Unix timestamp (seconds)
    float batteryLevel;
    int signalStrength;
};

// Memory buffer for offline readings
MedicalReading readingsBuffer[MAX_BUFFER_SIZE];
int bufferCount = 0;
int bufferReadIndex = 0;

// ==================== GLOBAL VARIABLES ====================

unsigned long lastReadingTime = 0;
unsigned long lastSendTime = 0;
unsigned long lastWiFiCheck = 0;
bool isOnline = false;
int consecutiveFailures = 0;

// ==================== SETUP ====================

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n\n====================================");
  Serial.println("   GharDoc Medical Device v1.0.0");
  Serial.println("   Rural Healthcare Monitoring");
  Serial.println("====================================\n");
  
  // Initialize sensors
  initializeSensors();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Print configuration
  printConfiguration();
  
  Serial.println("\n✅ System Ready! Starting monitoring...\n");
}

// ==================== MAIN LOOP ====================

void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi status periodically
  if (currentTime - lastWiFiCheck >= WIFI_RETRY_INTERVAL) {
    lastWiFiCheck = currentTime;
    checkWiFiConnection();
  }
  
  // Take reading at specified interval
  if (currentTime - lastReadingTime >= READING_INTERVAL) {
    lastReadingTime = currentTime;
    takeMedicalReading();
  }
  
  // If online, try to send buffered data
  if (isOnline && bufferCount > 0) {
    if (currentTime - lastSendTime >= SEND_INTERVAL) {
      lastSendTime = currentTime;
      sendBufferedData();
    }
  }
  
  delay(100);  // Small delay to prevent watchdog issues
}

// ==================== WIFI FUNCTIONS ====================

void connectToWiFi() {
  Serial.print("🔌 Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    isOnline = true;
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("📡 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("📶 Signal: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    isOnline = false;
    Serial.println("\n⚠️  WiFi Connection Failed - Operating in OFFLINE mode");
    Serial.println("   Readings will be stored and uploaded when online");
  }
}

void checkWiFiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!isOnline) {
      Serial.println("✅ WiFi connection restored!");
      isOnline = true;
    }
  } else {
    if (isOnline) {
      Serial.println("⚠️  WiFi connection lost - switching to OFFLINE mode");
      isOnline = false;
    }
    // Try to reconnect
    Serial.println("🔄 Attempting to reconnect to WiFi...");
    WiFi.reconnect();
  }
}

// ==================== SENSOR FUNCTIONS ====================

void initializeSensors() {
  Serial.println("🔧 Initializing sensors...");
  
  pinMode(TEMP_SENSOR_PIN, INPUT);
  pinMode(PULSE_SENSOR_PIN, INPUT);
  pinMode(SPO2_SENSOR_PIN, INPUT);
  
  Serial.println("✅ Sensors initialized\n");
}

float readBodyTemperature() {
  // Real sensor implementation:
  // int rawValue = analogRead(TEMP_SENSOR_PIN);
  // float voltage = (rawValue / 4095.0) * 3.3;
  // float tempC = (voltage - 0.5) * 100;  // Example for TMP36
  // float tempF = (tempC * 9.0 / 5.0) + 32.0;
  // return tempF;
  
  // SIMULATION (Remove in production):
  return 97.0 + random(0, 40) / 10.0;  // 97.0°F to 101.0°F
}

int readPulseRate() {
  // Real sensor implementation for pulse sensor
  // Implement peak detection algorithm
  
  // SIMULATION (Remove in production):
  return 60 + random(0, 40);  // 60-100 bpm
}

int readHeartRate() {
  // Can use same as pulse or separate ECG sensor
  
  // SIMULATION (Remove in production):
  return 60 + random(0, 40);  // 60-100 bpm
}

float readSpO2() {
  // Real implementation for MAX30102 or similar:
  // Calculate SpO2 from red and IR LED readings
  
  // SIMULATION (Remove in production):
  return 95.0 + random(0, 50) / 10.0;  // 95-100%
}

float readBatteryLevel() {
  // If using battery, read voltage and calculate percentage
  // Example for LiPo battery (3.0V-4.2V range):
  // int rawValue = analogRead(BATTERY_PIN);
  // float voltage = (rawValue / 4095.0) * 3.3 * 2;  // Assuming voltage divider
  // float percentage = map(voltage * 100, 300, 420, 0, 100);
  // return constrain(percentage, 0, 100);
  
  // For USB powered:
  return 100.0;
}

// ==================== DATA COLLECTION ====================

void takeMedicalReading() {
  Serial.println("\n📊 Taking medical reading...");
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  
  // Read all sensors
  float bodyTemp = readBodyTemperature();
  int pulse = readPulseRate();
  int heartRate = readHeartRate();
  float spo2 = readSpO2();
  float battery = readBatteryLevel();
  int signal = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
  
  // Display readings
  Serial.printf("🌡️  Body Temperature: %.1f °F\n", bodyTemp);
  Serial.printf("💓 Pulse Rate: %d bpm\n", pulse);
  Serial.printf("❤️  Heart Rate: %d bpm\n", heartRate);
  Serial.printf("🫁 SpO2: %.1f %%\n", spo2);
  Serial.printf("🔋 Battery: %.1f %%\n", battery);
  Serial.printf("📶 Signal: %d dBm\n", signal);
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  
  // Check for abnormal readings
  if (bodyTemp >= 100.4) {
    Serial.println("⚠️  WARNING: High temperature detected (Fever)!");
  }
  if (pulse > 120 || pulse < 50) {
    Serial.println("⚠️  WARNING: Abnormal pulse rate!");
  }
  if (spo2 < 90) {
    Serial.println("🚨 CRITICAL: Low oxygen saturation!");
  }
  
  // Store in buffer
  storeReading(bodyTemp, pulse, heartRate, spo2, battery, signal);
  
  // If online, try to send immediately
  if (isOnline) {
    sendSingleReading(bodyTemp, pulse, heartRate, spo2, battery, signal);
  } else {
    Serial.println("📴 Offline - Reading stored in memory buffer");
    Serial.printf("   Buffer: %d/%d readings\n", bufferCount, MAX_BUFFER_SIZE);
  }
}

void storeReading(float temp, int pulse, int hr, float spo2, float battery, int signal) {
  if (bufferCount < MAX_BUFFER_SIZE) {
    readingsBuffer[bufferCount].bodyTemperature = temp;
    readingsBuffer[bufferCount].pulseRate = pulse;
    readingsBuffer[bufferCount].heartRate = hr;
    readingsBuffer[bufferCount].spo2 = spo2;
    readingsBuffer[bufferCount].recordedAt = millis() / 1000;  // Unix timestamp
    readingsBuffer[bufferCount].batteryLevel = battery;
    readingsBuffer[bufferCount].signalStrength = signal;
    bufferCount++;
  } else {
    Serial.println("⚠️  Buffer full! Oldest reading will be overwritten");
    // Shift buffer and add new reading
    for (int i = 0; i < MAX_BUFFER_SIZE - 1; i++) {
      readingsBuffer[i] = readingsBuffer[i + 1];
    }
    readingsBuffer[MAX_BUFFER_SIZE - 1].bodyTemperature = temp;
    readingsBuffer[MAX_BUFFER_SIZE - 1].pulseRate = pulse;
    readingsBuffer[MAX_BUFFER_SIZE - 1].heartRate = hr;
    readingsBuffer[MAX_BUFFER_SIZE - 1].spo2 = spo2;
    readingsBuffer[MAX_BUFFER_SIZE - 1].recordedAt = millis() / 1000;
    readingsBuffer[MAX_BUFFER_SIZE - 1].batteryLevel = battery;
    readingsBuffer[MAX_BUFFER_SIZE - 1].signalStrength = signal;
  }
}

// ==================== DATA TRANSMISSION ====================

bool sendSingleReading(float temp, int pulse, int hr, float spo2, float battery, int signal) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  Serial.println("\n📤 Sending reading to backend...");
  
  HTTPClient http;
  http.setTimeout(10000);
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON
  StaticJsonDocument<512> doc;
  doc["user_id"] = USER_ID;
  doc["device_id"] = DEVICE_ID;
  doc["body_temperature"] = temp;
  doc["pulse_rate"] = pulse;
  doc["heart_rate"] = hr;
  doc["spo2"] = spo2;
  doc["battery_level"] = battery;
  doc["signal_strength"] = signal;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int responseCode = http.POST(jsonString);
  
  if (responseCode > 0) {
    Serial.printf("✅ Response: %d\n", responseCode);
    String response = http.getString();
    
    // Parse response to check for alerts
    StaticJsonDocument<512> responseDoc;
    deserializeJson(responseDoc, response);
    
    if (responseDoc["success"]) {
      if (responseDoc["data"]["alerts_triggered"].as<int>() > 0) {
        Serial.println("🚨 HEALTH ALERT TRIGGERED!");
      }
      consecutiveFailures = 0;
      
      // Remove this reading from buffer if it was stored
      if (bufferCount > 0 && bufferReadIndex < bufferCount) {
        bufferReadIndex++;
        bufferCount--;
      }
    }
    
    http.end();
    return true;
    
  } else {
    Serial.printf("❌ Send failed: %d\n", responseCode);
    consecutiveFailures++;
    http.end();
    return false;
  }
}

void sendBufferedData() {
  if (bufferCount == 0) {
    return;
  }
  
  Serial.printf("\n📦 Uploading buffered data: %d readings\n", bufferCount);
  
  // Send in batches
  int batchCount = 0;
  while (bufferCount > 0 && batchCount < 3) {  // Max 3 batches per attempt
    int batchSize = min(bufferCount, BATCH_SEND_SIZE);
    
    if (sendBatch(batchSize)) {
      Serial.printf("✅ Batch %d uploaded (%d readings)\n", batchCount + 1, batchSize);
      
      // Remove sent readings from buffer
      for (int i = 0; i < bufferCount - batchSize; i++) {
        readingsBuffer[i] = readingsBuffer[i + batchSize];
      }
      bufferCount -= batchSize;
      
      batchCount++;
      delay(2000);  // Delay between batches
    } else {
      Serial.println("❌ Batch upload failed, will retry later");
      break;
    }
  }
  
  if (bufferCount == 0) {
    Serial.println("✅ All buffered data uploaded successfully!");
    bufferReadIndex = 0;
  } else {
    Serial.printf("📴 %d readings remaining in buffer\n", bufferCount);
  }
}

bool sendBatch(int size) {
  if (WiFi.status() != WL_CONNECTED || size == 0) {
    return false;
  }
  
  HTTPClient http;
  http.setTimeout(15000);  // Longer timeout for batch
  http.begin(BATCH_URL);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON array
  DynamicJsonDocument doc(8192);  // Large buffer for batch
  doc["user_id"] = USER_ID;
  doc["device_id"] = DEVICE_ID;
  
  JsonArray readings = doc.createNestedArray("readings");
  
  for (int i = 0; i < size; i++) {
    JsonObject reading = readings.createNestedObject();
    reading["body_temperature"] = readingsBuffer[i].bodyTemperature;
    reading["pulse_rate"] = readingsBuffer[i].pulseRate;
    reading["heart_rate"] = readingsBuffer[i].heartRate;
    reading["spo2"] = readingsBuffer[i].spo2;
    reading["battery_level"] = readingsBuffer[i].batteryLevel;
    reading["signal_strength"] = readingsBuffer[i].signalStrength;
    
    // Format timestamp as ISO 8601
    char timestamp[32];
    unsigned long seconds = readingsBuffer[i].recordedAt;
    sprintf(timestamp, "2026-02-03T%02lu:%02lu:%02luZ", 
            (seconds / 3600) % 24, 
            (seconds / 60) % 60, 
            seconds % 60);
    reading["recorded_at"] = timestamp;
  }
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int responseCode = http.POST(jsonString);
  
  http.end();
  
  return (responseCode == 200 || responseCode == 201);
}

// ==================== UTILITY FUNCTIONS ====================

void printConfiguration() {
  Serial.println("\n⚙️  Configuration:");
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  Serial.printf("User ID: %d\n", USER_ID);
  Serial.printf("Device ID: %s\n", DEVICE_ID);
  Serial.printf("Server: %s\n", SERVER_URL);
  Serial.printf("Reading Interval: %lu seconds\n", READING_INTERVAL / 1000);
  Serial.printf("Buffer Size: %d readings\n", MAX_BUFFER_SIZE);
  Serial.printf("WiFi SSID: %s\n", WIFI_SSID);
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

// ==================== TROUBLESHOOTING ====================

/*
 * SETUP INSTRUCTIONS:
 * 
 * 1. Install Required Libraries:
 *    - ArduinoJson (by Benoit Blanchon)
 *    
 * 2. Update Configuration:
 *    - Set YOUR_WIFI_SSID and YOUR_WIFI_PASSWORD
 *    - Set SERVER_URL with your backend IP address
 *    - Set USER_ID after creating account in GharDoc
 *    
 * 3. Connect Sensors:
 *    - Temperature sensor → Pin 34
 *    - Pulse sensor → Pin 35
 *    - SpO2 sensor → Pin 32
 *    
 * 4. Upload Code to ESP32
 * 
 * 5. Open Serial Monitor (115200 baud) to see output
 * 
 * COMMON ISSUES:
 * 
 * - "WiFi Connection Failed"
 *   → Check SSID and password
 *   → ESP32 only supports 2.4GHz WiFi
 *   
 * - "Send failed: -1"
 *   → Backend not running
 *   → Wrong IP address in SERVER_URL
 *   → Firewall blocking connection
 *   
 * - "Buffer full"
 *   → Device offline too long
 *   → Increase MAX_BUFFER_SIZE if needed
 *   → Readings will be overwritten when buffer full
 *   
 * TESTING WITHOUT SENSORS:
 *   → Code uses simulated values
 *   → Replace simulation code with real sensor code
 *   → Test offline mode by disconnecting WiFi
 */
