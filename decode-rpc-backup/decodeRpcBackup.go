package main

/* Build with:
  go mod init decodeRpcBackup
  go mod tidy
  go build
*/

/* Run with:
  echo "encoded string" | ./decodeRpcBackup SecretValue
*/

import (
	"bufio"
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"strings"
)

// RightPad2Len pads string s to overallLen using padStr
func RightPad2Len(s, padStr string, overallLen int) string {
	padCountInt := 1 + (overallLen-len(padStr))/len(padStr)
	retStr := s + strings.Repeat(padStr, padCountInt)
	return retStr[:overallLen]
}

// GetPaddedString pads the string to 32 bytes using "=" as padding
func GetPaddedString(str string) []byte {
	return []byte(RightPad2Len(str, "=", 32))
}

// Decrypt decrypts base64 encoded cryptoText using AES CFB mode
func Decrypt(key []byte, cryptoText string) string {
	ciphertext, err := base64.URLEncoding.DecodeString(cryptoText)
	if err != nil {
		log.Printf("Error decoding base64: %v", err)
		return ""
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		log.Printf("Error creating AES cipher: %v", err)
		return ""
	}

	// The IV needs to be unique, but not secure. Therefore it's common to
	// include it at the beginning of the ciphertext.
	if len(ciphertext) < aes.BlockSize {
		log.Printf("Error: ciphertext too short")
		return ""
	}
	iv := ciphertext[:aes.BlockSize]
	ciphertext = ciphertext[aes.BlockSize:]

	stream := cipher.NewCFBDecrypter(block, iv)

	// XORKeyStream can work in-place if the two arguments are the same.
	stream.XORKeyStream(ciphertext, ciphertext)

	return string(ciphertext)
}

func main() {
	// Use "Secret" as the default secret, or take from command line argument
	secretStr := "Secret"
	if len(os.Args) > 1 {
		secretStr = os.Args[1]
	}
	secret := GetPaddedString(secretStr)

	// Read cryptoText from stdin
	scanner := bufio.NewScanner(os.Stdin)
	var cryptoText strings.Builder

	for scanner.Scan() {
		cryptoText.WriteString(scanner.Text())
		cryptoText.WriteString("\n")
	}

	if err := scanner.Err(); err != nil {
		log.Fatalf("Error reading from stdin: %v", err)
	}

	// Remove trailing newline if present
	input := strings.TrimSuffix(cryptoText.String(), "\n")

	if input == "" {
		log.Fatal("No input provided")
	}

	// Decrypt the text
	decrypted := Decrypt(secret, input)

	if decrypted == "" {
		log.Fatal("Decryption failed")
	}

	// Print decrypted text to stdout
	fmt.Print(decrypted)
}
