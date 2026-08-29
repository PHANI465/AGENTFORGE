// Package db is the auth-service's only access to Postgres — it reads and
// writes the `users` table that packages/common/alembic/versions/0003_add_tenancy.py
// created. No separate schema/migration tool for this service: one
// migration history (Alembic), auth-service just connects to the same
// database, same pattern as every Python service.
package db

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

var ErrNotFound = errors.New("not found")
var ErrEmailTaken = errors.New("email already registered")

type User struct {
	ID             string
	Email          string
	PasswordHash   *string
	OAuthProvider  *string
	OAuthSubject   *string
	Name           *string
	CreatedAt      time.Time
}

type DB struct {
	pool *pgxpool.Pool
}

func Connect(ctx context.Context, dsn string) (*DB, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("connecting to postgres: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("pinging postgres: %w", err)
	}
	return &DB{pool: pool}, nil
}

func (d *DB) Close() {
	d.pool.Close()
}

func (d *DB) Ping(ctx context.Context) error {
	return d.pool.Ping(ctx)
}

func scanUser(row pgx.Row) (User, error) {
	var u User
	err := row.Scan(&u.ID, &u.Email, &u.PasswordHash, &u.OAuthProvider, &u.OAuthSubject, &u.Name, &u.CreatedAt)
	return u, err
}

const userColumns = "id, email, password_hash, oauth_provider, oauth_subject, name, created_at"

func (d *DB) GetUserByEmail(ctx context.Context, email string) (User, error) {
	row := d.pool.QueryRow(ctx, "SELECT "+userColumns+" FROM users WHERE email = $1", email)
	u, err := scanUser(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return User{}, ErrNotFound
	}
	return u, err
}

func (d *DB) GetUserByID(ctx context.Context, id string) (User, error) {
	row := d.pool.QueryRow(ctx, "SELECT "+userColumns+" FROM users WHERE id = $1", id)
	u, err := scanUser(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return User{}, ErrNotFound
	}
	return u, err
}

func (d *DB) GetUserByOAuthSubject(ctx context.Context, provider, subject string) (User, error) {
	row := d.pool.QueryRow(ctx,
		"SELECT "+userColumns+" FROM users WHERE oauth_provider = $1 AND oauth_subject = $2",
		provider, subject)
	u, err := scanUser(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return User{}, ErrNotFound
	}
	return u, err
}

// CreateUserWithPassword inserts a new email+password account. Returns
// ErrEmailTaken if the unique constraint on users.email fires.
func (d *DB) CreateUserWithPassword(ctx context.Context, id, email, passwordHash string) (User, error) {
	row := d.pool.QueryRow(ctx,
		`INSERT INTO users (id, email, password_hash, created_at)
		 VALUES ($1, $2, $3, now())
		 RETURNING `+userColumns,
		id, email, passwordHash,
	)
	u, err := scanUser(row)
	if isUniqueViolation(err) {
		return User{}, ErrEmailTaken
	}
	return u, err
}

// FindOrCreateOAuthUser looks up a user by (provider, subject), creating
// one if this is their first login. email/name come from the provider's
// userinfo response and are only used to populate a brand-new row — an
// existing row's email/name aren't overwritten on repeat logins.
func (d *DB) FindOrCreateOAuthUser(ctx context.Context, id, provider, subject, email, name string) (User, error) {
	existing, err := d.GetUserByOAuthSubject(ctx, provider, subject)
	if err == nil {
		return existing, nil
	}
	if !errors.Is(err, ErrNotFound) {
		return User{}, err
	}

	row := d.pool.QueryRow(ctx,
		`INSERT INTO users (id, email, oauth_provider, oauth_subject, name, created_at)
		 VALUES ($1, $2, $3, $4, $5, now())
		 RETURNING `+userColumns,
		id, email, provider, subject, name,
	)
	u, insertErr := scanUser(row)
	if isUniqueViolation(insertErr) {
		// Someone with this email already signed up a different way
		// (password, or a different provider) — don't silently merge
		// accounts. The caller surfaces this as a normal 409.
		return User{}, ErrEmailTaken
	}
	return u, insertErr
}

func isUniqueViolation(err error) bool {
	if err == nil {
		return false
	}
	// pgx surfaces Postgres error code 23505 (unique_violation) via a
	// *pgconn.PgError with a Code field — checking the message substring
	// would be fragile across locales/versions, so this uses the
	// structured error instead. errors.As unwraps pgx's wrapping.
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}
