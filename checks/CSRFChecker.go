package main

// build with
// go mod init main
// go mod tidy
// go build CSRFChecker.go

import (
    "fmt"
    "os"

    "github.com/TykTechnologies/nosurf"
)

func main() {
    if len(os.Args) != 3 {
        fmt.Println("Usage: go run main.go <realToken> <sentToken>")
        os.Exit(1)
    }

    realToken := os.Args[1]
    sentToken := os.Args[2]

    result := nosurf.VerifyToken(realToken, sentToken)
    fmt.Printf("Tokens are equal: %v\n", result)
}
