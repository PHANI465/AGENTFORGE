package auth

import "golang.org/x/crypto/bcrypt"

// bcrypt's default cost (10) is deliberately not lowered — these are
// low-entropy user-chosen passwords (unlike AgentForge's API keys, which
// are high-entropy random tokens hashed with plain SHA-256 elsewhere in
// the platform; see packages/common/agentforge_common/security.py's own
// comment on that distinction). Passwords need the deliberately slow,
// salted hash bcrypt provides.
const bcryptCost = bcrypt.DefaultCost

func HashPassword(plaintext string) (string, error) {
	hash, err := bcrypt.GenerateFromPassword([]byte(plaintext), bcryptCost)
	if err != nil {
		return "", err
	}
	return string(hash), nil
}

// VerifyPassword returns true iff plaintext matches hash. bcrypt's
// CompareHashAndPassword is already constant-time with respect to the
// comparison itself.
func VerifyPassword(hash, plaintext string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(plaintext)) == nil
}
