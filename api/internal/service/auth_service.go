package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/Denter-/article-extraction/api/internal/config"
	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/Denter-/article-extraction/api/internal/repository"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	userRepo *repository.UserRepository
	cfg      *config.AuthConfig
}

func NewAuthService(userRepo *repository.UserRepository, cfg *config.AuthConfig) *AuthService {
	return &AuthService{
		userRepo: userRepo,
		cfg:      cfg,
	}
}

func (s *AuthService) Register(ctx context.Context, req *models.CreateUserRequest) (*models.User, error) {
	// Check if user exists
	existing, _ := s.userRepo.GetByEmail(ctx, req.Email)
	if existing != nil {
		return nil, fmt.Errorf("user already exists")
	}

	// Hash password
	passwordHash, err := bcrypt.GenerateFromPassword([]byte(req.Password), s.cfg.BcryptCost)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %w", err)
	}

	// Generate API key
	apiKey := generateAPIKey()

	user := &models.User{
		Email:        req.Email,
		PasswordHash: string(passwordHash),
		Tier:         models.TierFree,
		Credits:      10,
		APIKey:       &apiKey,
		IsActive:     true,
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	return user, nil
}

func (s *AuthService) Login(ctx context.Context, req *models.LoginRequest) (*models.LoginResponse, error) {
	user, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err != nil {
		return nil, fmt.Errorf("invalid credentials")
	}

	// Verify password
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)); err != nil {
		return nil, fmt.Errorf("invalid credentials")
	}

	// Update last login
	s.userRepo.UpdateLastLogin(ctx, user.ID)

	// Generate JWT
	token, err := s.generateJWT(user)
	if err != nil {
		return nil, fmt.Errorf("failed to generate token: %w", err)
	}

	return &models.LoginResponse{
		Token: token,
		User:  *user,
	}, nil
}

func (s *AuthService) ValidateToken(tokenString string) (*models.User, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method")
		}
		return []byte(s.cfg.JWTSecret), nil
	})

	if err != nil || !token.Valid {
		return nil, fmt.Errorf("invalid token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("invalid token claims")
	}

	userIDStr, ok := claims["user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("invalid user_id in token")
	}

	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid user_id format")
	}

	user, err := s.userRepo.GetByID(context.Background(), userID)
	if err != nil {
		return nil, fmt.Errorf("user not found")
	}

	return user, nil
}

func (s *AuthService) ValidateAPIKey(ctx context.Context, apiKey string) (*models.User, error) {
	user, err := s.userRepo.GetByAPIKey(ctx, apiKey)
	if err != nil {
		return nil, fmt.Errorf("invalid API key")
	}
	return user, nil
}

func (s *AuthService) generateJWT(user *models.User) (string, error) {
	claims := jwt.MapClaims{
		"user_id": user.ID.String(),
		"email":   user.Email,
		"tier":    user.Tier,
		"exp":     time.Now().Add(time.Hour * time.Duration(s.cfg.JWTExpiryHours)).Unix(),
		"iat":     time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(s.cfg.JWTSecret))
}

func generateAPIKey() string {
	b := make([]byte, 32)
	rand.Read(b)
	return hex.EncodeToString(b)
}
