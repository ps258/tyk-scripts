package gen

import (
	"math"
	"math/rand/v2"
)

// logNormalNoise returns a multiplier with median 1.
func logNormalNoise(r *rand.Rand, sigma float64) float64 {
	if sigma <= 0 {
		return 1
	}
	return math.Exp(r.NormFloat64() * sigma)
}

// poisson draws from Poisson(lambda), using a normal approximation for large lambda.
func poisson(r *rand.Rand, lambda float64) int {
	switch {
	case lambda <= 0:
		return 0
	case lambda < 30:
		l := math.Exp(-lambda)
		k, p := 0, 1.0
		for {
			p *= r.Float64()
			if p <= l {
				return k
			}
			k++
		}
	default:
		return max(0, int(math.Round(lambda+math.Sqrt(lambda)*r.NormFloat64())))
	}
}

// binomial draws from Binomial(n, p), using approximations for large n.
func binomial(r *rand.Rand, n int, p float64) int {
	switch {
	case n <= 0 || p <= 0:
		return 0
	case p >= 1:
		return n
	case n < 40:
		k := 0
		for range n {
			if r.Float64() < p {
				k++
			}
		}
		return k
	case float64(n)*p < 10:
		return min(n, poisson(r, float64(n)*p))
	default:
		mean := float64(n) * p
		sd := math.Sqrt(mean * (1 - p))
		return min(n, max(0, int(math.Round(mean+sd*r.NormFloat64()))))
	}
}

// multinomial splits n across weights.
func multinomial(r *rand.Rand, n int, weights []float64) []int {
	out := make([]int, len(weights))
	rest := 0.0
	for _, w := range weights {
		rest += w
	}
	for i, w := range weights {
		if n == 0 || rest <= 0 {
			break
		}
		if i == len(weights)-1 {
			out[i] = n
			break
		}
		k := binomial(r, n, w/rest)
		out[i] = k
		n -= k
		rest -= w
	}
	return out
}

// normInv is the inverse standard normal CDF (Acklam's approximation).
func normInv(p float64) float64 {
	const (
		a1, a2, a3, a4, a5, a6 = -3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00
		b1, b2, b3, b4, b5     = -5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01
		c1, c2, c3, c4, c5, c6 = -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00
		d1, d2, d3, d4         = 7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00
		lo, hi                 = 0.02425, 1 - 0.02425
	)
	switch {
	case p <= 0:
		return math.Inf(-1)
	case p >= 1:
		return math.Inf(1)
	case p < lo:
		q := math.Sqrt(-2 * math.Log(p))
		return (((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q + c6) / ((((d1*q+d2)*q+d3)*q+d4)*q + 1)
	case p > hi:
		q := math.Sqrt(-2 * math.Log(1-p))
		return -(((((c1*q+c2)*q+c3)*q+c4)*q+c5)*q + c6) / ((((d1*q+d2)*q+d3)*q+d4)*q + 1)
	default:
		q := p - 0.5
		t := q * q
		return (((((a1*t+a2)*t+a3)*t+a4)*t+a5)*t + a6) * q / (((((b1*t+b2)*t+b3)*t+b4)*t+b5)*t + 1)
	}
}

// zipfWeights returns n weights 1/rank^s, assigned to a seeded random permutation.
func zipfWeights(r *rand.Rand, n int, s float64) []float64 {
	w := make([]float64, n)
	for i, rank := range r.Perm(n) {
		w[i] = 1 / math.Pow(float64(rank+1), s)
	}
	return w
}

func normalize(w []float64) []float64 {
	sum := 0.0
	for _, v := range w {
		sum += v
	}
	out := make([]float64, len(w))
	if sum == 0 {
		return out
	}
	for i, v := range w {
		out[i] = v / sum
	}
	return out
}
