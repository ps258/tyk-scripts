package main

import (
	"crypto/md5"
	"encoding/base64"
	"flag"
	"fmt"
)

func main() {

	orgID := flag.String("Orgid", "", "Organisation ID")
	baseFieldData := flag.String("Sub", "", "JWT Sub value")
	hashAlgorithm := flag.String("HashAlgorithm", "", "Hash Algorithm")
	flag.Parse()

	//	fmt.Printf(`{"org":"%s","id":"%s","h":"%s"}`, *orgID, *baseFieldData, *hashAlgorithm)
	//	fmt.Println()

	data := []byte(*baseFieldData)
	keyID := fmt.Sprintf("%x", md5.Sum(data))

	jsonToken := fmt.Sprintf(`{"org":"%s","id":"%s","h":"%s"}`, *orgID, keyID, *hashAlgorithm)
	fmt.Println("token is " + jsonToken)
	fmt.Println("Session ID is " + base64.StdEncoding.EncodeToString([]byte(jsonToken)))
}
