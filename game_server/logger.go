package main

import (
	"fmt"
	"time"
)

//print warning to stdout
func Warning(format string, v ...interface{}) {
	message := fmt.Sprintf(format, v...)
	fmt.Println("\033[93mWARNING : " +
		time.Now().UTC().Format(time.RFC3339) + " : " + message + "\033[0m")
}

//print error to stdout
func Error(format string, v ...interface{}) {
	message := fmt.Sprintf(format, v...)
	fmt.Println("\033[91mERROR : " +
		time.Now().UTC().Format(time.RFC3339) + " : " + message + "\033[0m")
}

//print info to stdout
func Info(format string, v ...interface{}) {
	message := fmt.Sprintf(format, v...)
	fmt.Println("\033[94mINFO : " +
		time.Now().UTC().Format(time.RFC3339) + " : " + message + "\033[0m")
}
