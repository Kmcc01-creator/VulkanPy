package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type Message struct {
	Text string `json:"text"`
}

func hello(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	msg := Message{Text: "Hello from Go!"}
	json.NewEncoder(w).Encode(msg)
}

func main() {
	http.HandleFunc("/", hello)
	fmt.Println("Server listening on port 8080")
	http.ListenAndServe(":8080", nil)
}
