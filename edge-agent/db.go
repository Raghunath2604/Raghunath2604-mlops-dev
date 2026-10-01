package main

import (
	"database/sql"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

var db *sql.DB

type Event struct {
	ID        int
	Type      string
	Payload   string
	CreatedAt time.Time
}

func initDB() error {
	configDir := "/etc/mlops"
	if _, err := os.Stat(configDir); os.IsNotExist(err) {
		// fallback to local for dev
		configDir = "."
	}
	dbPath := filepath.Join(configDir, "agent.db")

	var err error
	db, err = sql.Open("sqlite", dbPath)
	if err != nil {
		return err
	}

	createTableQuery := `
	CREATE TABLE IF NOT EXISTS events (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		type TEXT NOT NULL,
		payload TEXT NOT NULL,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);
	`
	_, err = db.Exec(createTableQuery)
	return err
}

func queueEvent(eventType string, payload interface{}) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = db.Exec("INSERT INTO events (type, payload) VALUES (?, ?)", eventType, string(data))
	return err
}

func getPendingEvents() ([]Event, error) {
	rows, err := db.Query("SELECT id, type, payload, created_at FROM events ORDER BY id ASC LIMIT 50")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var events []Event
	for rows.Next() {
		var e Event
		err = rows.Scan(&e.ID, &e.Type, &e.Payload, &e.CreatedAt)
		if err != nil {
			log.Println("Error scanning event row:", err)
			continue
		}
		events = append(events, e)
	}
	return events, nil
}

func deleteEvent(id int) error {
	_, err := db.Exec("DELETE FROM events WHERE id=?", id)
	return err
}
