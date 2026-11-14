variable "environment_authorized" {
  description = "True only after this dedicated environment, deployer and credit quota have been explicitly authorized."
  type        = bool
  default     = false
}

variable "prefix" {
  description = "Dedicated objects use this simple uppercase prefix; existing shared objects must not be imported implicitly."
  type        = string
  default     = "MDM_DEMO"
  validation {
    condition     = can(regex("^[A-Z][A-Z0-9_]{2,39}$", var.prefix))
    error_message = "prefix must be an uppercase SQL identifier, 3 to 40 characters."
  }
}

variable "total_credit_quota" {
  description = "Non-renewing warehouse credit quota. Resource monitors are an operational limit, not a guarantee of exact billing."
  type        = number
  default     = 1
  validation {
    condition     = var.total_credit_quota >= 1 && var.total_credit_quota <= 10
    error_message = "The qualification profile permits 1 to 10 total credits; larger budgets require a reviewed profile."
  }
}
