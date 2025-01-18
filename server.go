package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
)

type Message struct {
	Text string `json:"text"`
}

func hello(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method == http.MethodPost {
		body, err := ioutil.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Error reading request body", http.StatusBadRequest)
			return
		}

		var msg Message
		err = json.Unmarshal(body, &msg)
		if err != nil {
			http.Error(w, "Error unmarshalling JSON", http.StatusBadRequest)
			return
		}

		fmt.Printf("Received message: %s\n", msg.Text)
		json.NewEncoder(w).Encode(msg) // Echo the message back
		return
	}

	msg := Message{Text: "Hello from Go!"}
	json.NewEncoder(w).Encode(msg)
}

func main() {
	http.HandleFunc("/", hello)
	fmt.Println("Server listening on port 8080")
	http.ListenAndServe(":8080", nil)
}
