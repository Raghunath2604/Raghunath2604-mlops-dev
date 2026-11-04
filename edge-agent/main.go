package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"runtime"
	"strings"
	"time"
)

var (
	apiKey    string
	apiUrl    string
	deviceID  string
	hwClass   string
	modelName string
	modelTag  string
	baseline  []int32
)

func main() {
	log.Println("Starting MLOps.dev Edge Agent (Go 1.22)")

	// Parse basic config
	apiKey = os.Getenv("MLOPS_API_KEY")
	apiUrl = os.Getenv("MLOPS_API_URL")
	if apiUrl == "" {
		apiUrl = "https://api.mlops.dev/v1"
	}
	deviceID = getDeviceID()
	hwClass = "x86_64" // default
	if runtime.GOARCH == "arm64" {
		hwClass = "arm64"
	}

	err := initDB()
	if err != nil {
		log.Fatal("Failed to init SQLite:", err)
	}

	// Capture baseline (mocked for now)
	baseline = MockInputDistribution()

	// Sync loop
	for {
		err := syncWithControlPlane()
		if err != nil {
			log.Println("Sync error (buffered offline):", err)
		} else {
			flushOfflineBuffer()
		}
		time.Sleep(30 * time.Second)
	}
}

func getDeviceID() string {
	// In production, read /etc/machine-id
	idBytes, err := os.ReadFile("/etc/machine-id")
	if err == nil {
		return strings.TrimSpace(string(idBytes))
	}
	return "dev_go_agent_001"
}

func syncWithControlPlane() error {
	// Calculate current drift
	currentDist := MockInputDistribution() // mocked
	klScore := ComputeKL(baseline, currentDist)

	status := "online"
	if klScore > 0.7 {
		status = "drift"
	} else if klScore > 0.4 {
		status = "warning"
	}

	payload := map[string]interface{}{
		"drift_score": klScore,
		"status":      status,
		"cpu_pct":     getCPU(),
		"ram_mb":      getRAM(),
		"temp_c":      getTemp(),
		"uptime_s":    getUptime(),
	}

	// Queue telemetry locally
	queueEvent("heartbeat", payload)

	// Attempt to push
	return pushTelemetry(payload)
}

func pushTelemetry(payload map[string]interface{}) error {
	data, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", fmt.Sprintf("%s/devices/%s/heartbeat", apiUrl, deviceID), bytes.NewBuffer(data))
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	// Process sync instructions (e.g. download bsdiff patch)
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)

	if data, ok := result["data"].(map[string]interface{}); ok {
		if newName, ok := data["model_name"].(string); ok && newName != modelName {
			// Trigger bsdiff update
			log.Printf("New model instruction: %s:%s", newName, data["model_tag"])
			// Download and apply bsdiff...
			modelName = newName
			modelTag = data["model_tag"].(string)
		}
	}
	return nil
}

func flushOfflineBuffer() {
	events, err := getPendingEvents()
	if err != nil || len(events) == 0 {
		return
	}
	log.Printf("Flushing %d offline events", len(events))
	for _, e := range events {
		// Mock: just push the payload. If success, delete from DB.
		deleteEvent(e.ID)
	}
}

// System stat mocks
func getCPU() float64  { return 12.5 }
func getRAM() int      { return 1024 }
func getTemp() float64 { return 45.0 }
func getUptime() int   { return 3600 }
