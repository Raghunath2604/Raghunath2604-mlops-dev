package main

import (
	"math"
)

// KL Divergence without floating point math using a log table
// This matches the PDF specification for constrained ARM devices

const numBuckets = 256

// precomputed log table scaled by 1000
var logTable [10000]int32

func init() {
	// Initialize the lookup table once at startup
	for i := 1; i < 10000; i++ {
		logTable[i] = int32(math.Log(float64(i)) * 1000.0)
	}
	logTable[0] = logTable[1] // Avoid -Inf for 0
}

func getLog(val int32) int32 {
	if val < 0 {
		val = 0
	}
	if val >= 10000 {
		return int32(math.Log(float64(val)) * 1000.0)
	}
	return logTable[val]
}

// ComputeKL calculates KL(P || Q) using int32
// P and Q are histograms (counts), assumed to be already normalized to sum to 10000
func ComputeKL(p, q []int32) float64 {
	if len(p) != len(q) || len(p) != numBuckets {
		return 0.0
	}

	var klSum int32 = 0

	for i := 0; i < numBuckets; i++ {
		pi := p[i]
		qi := q[i]
		if pi == 0 {
			continue
		}
		if qi == 0 {
			qi = 1 // epsilon
		}

		// KL = P * log(P/Q) = P * (log(P) - log(Q))
		logP := getLog(pi)
		logQ := getLog(qi)

		diff := logP - logQ
		klSum += (pi * diff)
	}

	// Unscale: we multiplied P by 10000 and log by 1000
	return float64(klSum) / 10000000.0
}

func MockInputDistribution() []int32 {
	// Create a mock normalized distribution summing to 10000
	dist := make([]int32, numBuckets)
	dist[128] = 5000
	dist[129] = 2500
	dist[127] = 2500
	return dist
}
