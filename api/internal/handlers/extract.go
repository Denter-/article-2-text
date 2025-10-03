package handlers

import (
	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/Denter-/article-extraction/api/internal/service"
	"github.com/go-playground/validator/v10"
	"github.com/gofiber/fiber/v2"
)

type ExtractHandler struct {
	jobSvc    *service.JobService
	validator *validator.Validate
}

func NewExtractHandler(jobSvc *service.JobService) *ExtractHandler {
	return &ExtractHandler{
		jobSvc:    jobSvc,
		validator: validator.New(),
	}
}

func (h *ExtractHandler) ExtractSingle(c *fiber.Ctx) error {
	user, ok := c.Locals("user").(*models.User)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Unauthorized",
		})
	}

	var req models.CreateJobRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if err := h.validator.Struct(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	job, err := h.jobSvc.CreateJob(c.Context(), user.ID, &req)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"job":     job,
		"message": "Job queued for processing",
	})
}

func (h *ExtractHandler) ExtractBatch(c *fiber.Ctx) error {
	user, ok := c.Locals("user").(*models.User)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Unauthorized",
		})
	}

	var req models.CreateBatchJobRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	if err := h.validator.Struct(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	jobs, err := h.jobSvc.CreateBatchJobs(c.Context(), user.ID, &req)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"jobs":    jobs,
		"count":   len(jobs),
		"message": "Batch jobs queued for processing",
	})
}


