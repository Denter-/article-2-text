package handlers

import (
	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/Denter-/article-extraction/api/internal/service"
	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

type JobHandler struct {
	jobSvc *service.JobService
}

func NewJobHandler(jobSvc *service.JobService) *JobHandler {
	return &JobHandler{
		jobSvc: jobSvc,
	}
}

func (h *JobHandler) GetJob(c *fiber.Ctx) error {
	user, ok := c.Locals("user").(*models.User)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Unauthorized",
		})
	}

	jobIDStr := c.Params("id")
	jobID, err := uuid.Parse(jobIDStr)
	if err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid job ID",
		})
	}

	job, err := h.jobSvc.GetJob(c.Context(), jobID, user.ID)
	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"job": job,
	})
}

func (h *JobHandler) ListJobs(c *fiber.Ctx) error {
	user, ok := c.Locals("user").(*models.User)
	if !ok {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Unauthorized",
		})
	}

	limit := c.QueryInt("limit", 20)
	jobs, err := h.jobSvc.ListUserJobs(c.Context(), user.ID, limit)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": err.Error(),
		})
	}

	return c.JSON(fiber.Map{
		"jobs":  jobs,
		"count": len(jobs),
	})
}


