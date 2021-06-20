package main

import (
	"archive/zip"
	"bytes"
	"log"
	"net/http"
	"os"

	"github.com/jhoonb/archivex"
)

func zipDirectory(source string) *bytes.Buffer {
	buf := new(bytes.Buffer)
	w := zip.NewWriter(buf)
	defer w.Close()
	err := (&archivex.ZipFile{
		Writer: w,
		Name:   "waat",
	}).AddAll(source, false)

	if err != nil {
		log.Fatalf("Could not zip the output directory: %s", err)
	}
	return buf
}

func upload(data *bytes.Buffer, dest string) {
	client := &http.Client{}
	req, err := http.NewRequest(http.MethodPut, dest, data)
	if err != nil {
		log.Fatalf("Could not create an upload request: %s", err)
	}
	req.Header.Set("Content-Type", "application/zip")
	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("Could not perform the upload request: %s", err)
	}
	if resp.StatusCode != http.StatusCreated {
		log.Fatalf("Got a bad status code from ksci during upload: %d", resp.StatusCode)
	}
}

func main() {
	outputUrl := os.Getenv("KSCI_OUTPUT_URL")
	outputDir := os.Getenv("KSCI_OUTPUT_DIR")

	data := zipDirectory(outputDir)
	upload(data, outputUrl)
}
