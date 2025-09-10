# Infrastructure Setup - AWS Cognito with Terraform

## Overview

This document provides detailed Terraform configuration for setting up AWS Cognito with Google OAuth, including comprehensive explanations for junior DevOps engineers learning Terraform.

## What is Terraform?

Terraform is an Infrastructure as Code (IaC) tool that lets you define and provision cloud resources using configuration files. Instead of clicking through AWS Console, you write code that describes your infrastructure, and Terraform creates it for you.

**Key Benefits:**
- **Version Control**: Your infrastructure is code, so you can track changes
- **Reproducible**: Same code creates identical infrastructure every time  
- **Collaborative**: Team can review infrastructure changes like code
- **Documentation**: The code itself documents your infrastructure

## Terraform Core Concepts

### 1. Resources
Resources are the basic building blocks - they represent infrastructure objects like EC2 instances, databases, or in our case, Cognito components.

```hcl
resource "resource_type" "local_name" {
  # Configuration arguments
}
```

### 2. Variables
Variables make your code reusable and configurable:

```hcl
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
```

### 3. Data Sources
Data sources let you fetch information about existing resources:

```hcl
data "aws_caller_identity" "current" {}
# Use with: data.aws_caller_identity.current.account_id
```

### 4. Outputs
Outputs expose values from your infrastructure:

```hcl
output "user_pool_id" {
  value = aws_cognito_user_pool.play_later.id
}
```

## AWS Cognito Infrastructure Components

Our authentication system requires several interconnected AWS resources. Here's how they work together:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Pool     │────│ Identity Provider │────│  Google OAuth   │
│  (User Store)   │    │   (Google IDP)    │    │   (External)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         │
┌─────────────────┐    ┌──────────────────┐
│ User Pool Client│────│ User Pool Domain │
│ (App Settings)  │    │ (Hosted UI URL)  │
└─────────────────┘    └──────────────────┘
```

## File Structure

```
infra/
├── main.tf          # Main resources
├── variables.tf     # Input variables  
├── outputs.tf       # Output values
├── terraform.tf     # Terraform and provider settings
└── environments/
    ├── dev.tfvars   # Development variables
    └── prod.tfvars  # Production variables
```

## Complete Terraform Configuration

### 1. Terraform Configuration (terraform.tf)
```hcl
# terraform.tf - Defines Terraform and provider requirements
terraform {
  # Minimum Terraform version required
  required_version = ">= 1.0"
  
  # Required providers and their versions
  required_providers {
    aws = {
      source  = "hashicorp/aws"  # Official AWS provider
      version = "~> 5.0"         # Any 5.x version
    }
  }
  
  # Optional: Store state remotely (recommended for teams)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "play-later/terraform.state"
  #   region = "us-east-1"
  # }
}

# Configure the AWS provider
provider "aws" {
  region = var.aws_region
  
  # Optional: Add default tags to all resources
  default_tags {
    tags = {
      Project     = "play-later"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

### 2. Variables Definition (variables.tf)
```hcl
# variables.tf - Define all input variables with validation

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
  
  validation {
    condition = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in format: us-east-1, eu-west-1, etc."
  }
}

variable "environment" {
  description = "Environment name (affects resource naming)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "google_client_id" {
  description = "Google OAuth client ID (from Google Cloud Console)"
  type        = string
  sensitive   = true  # Terraform won't display this in logs
}

variable "google_client_secret" {
  description = "Google OAuth client secret (from Google Cloud Console)"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Your application domain (for callbacks)"
  type        = string
  
  validation {
    condition = can(regex("^[a-z0-9.-]+\\.[a-z]{2,}$", var.domain_name))
    error_message = "Domain must be valid format: example.com"
  }
}

variable "callback_urls" {
  description = "List of allowed callback URLs for OAuth"
  type        = list(string)
  default     = []
}
```

### 3. Main Infrastructure (main.tf)
```hcl
# main.tf - Main infrastructure resources

# ═══════════════════════════════════════════════════════════════
# 1. COGNITO USER POOL - The main user directory
# ═══════════════════════════════════════════════════════════════

resource "aws_cognito_user_pool" "play_later" {
  # Name shown in AWS Console
  name = "${var.environment}-play-later-users"
  
  # ─── User Registration Settings ───
  admin_create_user_config {
    # Allow users to self-register (not admin-only)
    allow_admin_create_user_only = false
    
    # Optional: Configure invitation messages
    invite_message_action = "EMAIL"
  }
  
  # ─── Email Configuration ───
  # Attributes that are automatically verified when user signs up
  auto_verified_attributes = ["email"]
  
  # Email verification settings
  verification_message_template {
    default_email_option  = "CONFIRM_WITH_CODE"
    email_subject        = "Your Play Later verification code"
    email_message        = "Your verification code is {####}"
  }
  
  # ─── User Attributes Schema ───
  # Define what information we store about users
  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true    # Must provide during signup
    mutable           = true     # Can change after signup
  }
  
  schema {
    attribute_data_type = "String" 
    name               = "given_name"  # First name
    required           = false
    mutable           = true
  }
  
  schema {
    attribute_data_type = "String"
    name               = "family_name"  # Last name  
    required           = false
    mutable           = true
  }
  
  # ─── Password Policy ───
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false  # Keep simple for OAuth users
    require_uppercase = true
  }
  
  # ─── Account Recovery ───
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
  
  # ─── Tagging ───
  tags = {
    Name = "${var.environment}-play-later-user-pool"
  }
}

# ═══════════════════════════════════════════════════════════════
# 2. GOOGLE IDENTITY PROVIDER - Connects to Google OAuth
# ═══════════════════════════════════════════════════════════════

resource "aws_cognito_identity_provider" "google" {
  # Link to our User Pool (reference to resource above)
  user_pool_id  = aws_cognito_user_pool.play_later.id
  provider_name = "Google"     # Must be exactly "Google"
  provider_type = "Google"     # AWS provider type
  
  # Google OAuth configuration
  provider_details = {
    # From Google Cloud Console OAuth 2.0 Client
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    # What permissions we request from Google
    authorize_scopes = "openid email profile"
  }
  
  # Map Google user attributes to Cognito attributes  
  attribute_mapping = {
    email         = "email"           # Google email → Cognito email
    given_name    = "given_name"      # Google first name → Cognito given_name  
    family_name   = "family_name"     # Google last name → Cognito family_name
    username      = "sub"             # Google user ID → Cognito username
  }
}

# ═══════════════════════════════════════════════════════════════
# 3. USER POOL CLIENT - App-specific settings
# ═══════════════════════════════════════════════════════════════

resource "aws_cognito_user_pool_client" "play_later" {
  name         = "${var.environment}-play-later-client"
  user_pool_id = aws_cognito_user_pool.play_later.id
  
  # ─── OAuth Configuration ───
  # Where Cognito can redirect after successful login
  callback_urls = concat([
    "https://api.${var.domain_name}/auth/callback",    # Production
    "http://localhost:8000/auth/callback",              # Development
  ], var.callback_urls)  # Additional URLs from variables
  
  # Where to redirect after logout
  logout_urls = [
    "https://${var.domain_name}/logout",
    "http://localhost:3000/logout"
  ]
  
  # OAuth flow types allowed
  allowed_oauth_flows = ["code"]  # Authorization Code flow (most secure)
  
  # What information the app can access
  allowed_oauth_scopes = [
    "openid",   # Basic OpenID Connect
    "email",    # User's email address  
    "profile"   # User's profile info
  ]
  
  # Which identity providers this client can use
  supported_identity_providers = [
    "Google",
    # "COGNITO"  # Uncomment if you want username/password login too
  ]
  
  # ─── Security Settings ───
  # Authentication flows allowed for this client
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",        # Secure Remote Password
    "ALLOW_REFRESH_TOKEN_AUTH"    # Allow token refresh
  ]
  
  # Security best practices
  generate_secret                = true   # Generate client secret
  prevent_user_existence_errors  = "ENABLED"  # Don't reveal if user exists
  
  # ─── Token Settings ───
  # How long tokens are valid (in minutes)
  access_token_validity  = 60    # 1 hour
  id_token_validity     = 60    # 1 hour  
  refresh_token_validity = 30   # 30 days
  
  # Token validity units
  token_validity_units {
    access_token  = "minutes"
    id_token     = "minutes"
    refresh_token = "days"
  }
  
  # Dependency: Wait for Google provider to be created first
  depends_on = [aws_cognito_identity_provider.google]
}

# ═══════════════════════════════════════════════════════════════
# 4. USER POOL DOMAIN - Creates Hosted UI URL
# ═══════════════════════════════════════════════════════════════

resource "aws_cognito_user_pool_domain" "play_later" {
  # This creates a URL like: https://play-later-dev.auth.us-east-1.amazoncognito.com
  domain       = "${var.environment}-play-later"
  user_pool_id = aws_cognito_user_pool.play_later.id
  
  # Alternative: Use custom domain (requires certificate)
  # certificate_arn = aws_acm_certificate.auth_domain.arn
  # domain         = "auth.${var.domain_name}"
}

# ═══════════════════════════════════════════════════════════════
# 5. OPTIONAL: CUSTOM DOMAIN (requires ACM certificate)
# ═══════════════════════════════════════════════════════════════

# Uncomment if you want custom domain like auth.yoursite.com
# resource "aws_acm_certificate" "auth_domain" {
#   domain_name       = "auth.${var.domain_name}"
#   validation_method = "DNS"
#   
#   lifecycle {
#     create_before_destroy = true
#   }
# }
```

### 4. Outputs (outputs.tf)
```hcl
# outputs.tf - Export important values for use in other systems

output "user_pool_id" {
  description = "Cognito User Pool ID (for backend configuration)"
  value       = aws_cognito_user_pool.play_later.id
}

output "user_pool_client_id" {
  description = "Cognito Client ID (for OAuth configuration)"
  value       = aws_cognito_user_pool_client.play_later.id
}

output "user_pool_client_secret" {
  description = "Cognito Client Secret (keep secure!)"
  value       = aws_cognito_user_pool_client.play_later.client_secret
  sensitive   = true  # Won't show in terminal output
}

output "cognito_domain" {
  description = "Cognito Hosted UI domain"
  value       = aws_cognito_user_pool_domain.play_later.domain
}

output "cognito_hosted_ui_url" {
  description = "Complete Cognito Hosted UI URL"
  value       = "https://${aws_cognito_user_pool_domain.play_later.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "google_identity_provider_name" {
  description = "Google Identity Provider name (for OAuth URLs)"
  value       = aws_cognito_identity_provider.google.provider_name
}

# Helper outputs for application configuration
output "environment_variables" {
  description = "Environment variables for your application"
  value = {
    AWS_REGION                = var.aws_region
    COGNITO_USER_POOL_ID     = aws_cognito_user_pool.play_later.id
    COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.play_later.id
    COGNITO_CLIENT_SECRET    = aws_cognito_user_pool_client.play_later.client_secret
    COGNITO_DOMAIN           = "${aws_cognito_user_pool_domain.play_later.domain}.auth.${var.aws_region}.amazoncognito.com"
  }
  sensitive = true
}
```

## Environment-Specific Variables

### Development (environments/dev.tfvars)
```hcl
# dev.tfvars - Development environment variables
environment = "dev"
aws_region  = "us-east-1"
domain_name = "play-later.com"

# Additional callback URLs for development
callback_urls = [
  "http://127.0.0.1:8000/auth/callback",
  "http://localhost:8001/auth/callback"  # Alternative port
]
```

### Production (environments/prod.tfvars)
```hcl
# prod.tfvars - Production environment variables  
environment = "prod"
aws_region  = "us-east-1"
domain_name = "play-later.com"

# Production might have additional callback URLs
callback_urls = [
  "https://api.play-later.com/auth/callback",
  "https://admin.play-later.com/auth/callback"
]
```

## Terraform Workflow & Commands

### Essential Commands

#### Basic Workflow
```bash
# Navigate to infrastructure directory
cd infra/

# Initialize Terraform (downloads providers, modules)
terraform init

# Format code (makes it pretty and consistent)
terraform fmt -recursive

# Validate syntax and configuration
terraform validate

# Plan changes (preview what will be created/changed)
terraform plan -var-file="environments/dev.tfvars"

# Apply changes (create/update infrastructure)
terraform apply -var-file="environments/dev.tfvars"

# Destroy infrastructure (careful!)
terraform destroy -var-file="environments/dev.tfvars"
```

#### Advanced Commands
```bash
# Show current state
terraform show

# List all resources in state
terraform state list

# Import existing AWS resource into Terraform state
terraform import aws_cognito_user_pool.play_later us-east-1_AbCdEfGhI

# View specific resource details
terraform state show aws_cognito_user_pool.play_later

# Refresh state (sync with actual AWS resources)
terraform refresh -var-file="environments/dev.tfvars"

# View outputs
terraform output

# View sensitive outputs  
terraform output -json | jq '.environment_variables.value'
```

## Validation Checklist for AI-Generated Terraform

When validating AI-generated Terraform code, check these critical areas:

### ✅ Resource Naming & Organization
```hcl
# ❌ BAD: Generic names, hard to identify
resource "aws_cognito_user_pool" "pool" {
  name = "my-pool"
}

# ✅ GOOD: Clear, descriptive names with environment
resource "aws_cognito_user_pool" "play_later" {
  name = "${var.environment}-play-later-users"
}
```

### ✅ Variable Validation & Security
```hcl
# ❌ BAD: No validation, secrets not marked
variable "client_secret" {
  type = string
}

# ✅ GOOD: Validation and security
variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.google_client_secret) > 20
    error_message = "Client secret must be at least 20 characters."
  }
}
```

### ✅ Resource Dependencies
```hcl
# ❌ BAD: Missing explicit dependency
resource "aws_cognito_user_pool_client" "app" {
  user_pool_id = aws_cognito_user_pool.main.id
  supported_identity_providers = ["Google"]  # May fail if Google IDP not ready
}

# ✅ GOOD: Explicit dependency
resource "aws_cognito_user_pool_client" "app" {
  user_pool_id = aws_cognito_user_pool.main.id
  supported_identity_providers = ["Google"]
  depends_on = [aws_cognito_identity_provider.google]  # Wait for Google IDP
}
```

### ✅ Output Security
```hcl
# ❌ BAD: Sensitive data exposed
output "client_secret" {
  value = aws_cognito_user_pool_client.app.client_secret
}

# ✅ GOOD: Marked as sensitive
output "client_secret" {
  value     = aws_cognito_user_pool_client.app.client_secret
  sensitive = true
}
```

## Common Pitfalls & Solutions

### 🚨 Problem 1: State File Conflicts
```bash
# Issue: Multiple people working on same infrastructure
Error: state lock

# Solutions:
# 1. Use remote state backend
terraform {
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "play-later/terraform.state" 
    region = "us-east-1"
    dynamodb_table = "terraform-state-locks"  # For state locking
  }
}

# 2. Force unlock if stuck (use carefully!)
terraform force-unlock <LOCK_ID>
```

### 🚨 Problem 2: Resource Naming Conflicts
```bash
# Issue: Resources already exist with same name
Error: resource already exists

# Solutions:
# 1. Import existing resource
terraform import aws_cognito_user_pool.play_later us-east-1_ExistingPoolId

# 2. Use unique naming with random suffix
resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_cognito_user_pool" "play_later" {
  name = "${var.environment}-play-later-${random_id.suffix.hex}"
}
```

### 🚨 Problem 3: Circular Dependencies
```hcl
# ❌ BAD: A depends on B, B depends on A
resource "aws_security_group" "app" {
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    security_groups = [aws_security_group.db.id]  # A → B
  }
}

resource "aws_security_group" "db" {
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [aws_security_group.app.id]  # B → A (circular!)
  }
}

# ✅ GOOD: Use security group rules separately
resource "aws_security_group_rule" "app_to_db" {
  type                     = "egress"
  from_port               = 5432
  to_port                 = 5432
  protocol                = "tcp"
  security_group_id       = aws_security_group.app.id
  source_security_group_id = aws_security_group.db.id
}
```

## AWS Cognito Specific Gotchas

### 1. Domain Availability
```bash
# Issue: Domain names must be globally unique
Error: domain already exists

# Solution: Use environment prefixes
domain = "${var.environment}-${var.project_name}-${random_id.domain_suffix.hex}"
```

### 2. Identity Provider Timing
```hcl
# Issue: Client tries to use Google before it's configured
# Solution: Explicit dependency
resource "aws_cognito_user_pool_client" "app" {
  # ... configuration ...
  depends_on = [aws_cognito_identity_provider.google]
}
```

### 3. Attribute Mapping Conflicts
```hcl
# Issue: Can't change attribute mapping after creation
# Solution: Plan for this in initial setup
attribute_mapping = {
  email      = "email"
  given_name = "given_name" 
  family_name = "family_name"
  username   = "sub"       # Use Google's unique ID as username
}
```

### 4. Token Validity Limits
```hcl
# AWS has limits on token validity periods
token_validity_units {
  access_token  = "minutes"  # 5 min - 1 day
  id_token     = "minutes"  # 5 min - 1 day  
  refresh_token = "days"    # 1 day - 10 years
}
```

## Security Best Practices

### 1. Secrets Management
```bash
# ❌ NEVER do this - secrets in plain text
terraform apply -var="google_client_secret=my-secret-123"

# ✅ Use environment variables
export TF_VAR_google_client_secret="your-secret-from-1password"
terraform apply -var-file="environments/dev.tfvars"

# ✅ Or use AWS Systems Manager Parameter Store
data "aws_ssm_parameter" "google_client_secret" {
  name = "/play-later/dev/google-client-secret"
  with_decryption = true
}
```

### 2. State File Security
```hcl
# ✅ Encrypt remote state
terraform {
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "play-later/terraform.state"
    region         = "us-east-1"
    encrypt        = true                    # Encrypt at rest
    dynamodb_table = "terraform-locks"
    
    # Version the state file
    versioning = true
  }
}
```

## Pre-Production Checklist

Before applying Terraform to production:

- [ ] All secrets properly managed (not in code)
- [ ] Resource naming follows conventions  
- [ ] State backend configured with encryption
- [ ] Variable validation rules in place
- [ ] Outputs marked as sensitive where needed
- [ ] Dependencies explicitly defined
- [ ] Tags applied for cost tracking/compliance
- [ ] Plan reviewed by team member
- [ ] Backup/disaster recovery tested
- [ ] Monitoring and alerting configured

## Next Steps

1. **Set up Google OAuth**: Configure OAuth client in Google Cloud Console
2. **Deploy infrastructure**: Run Terraform with development variables
3. **Validate setup**: Test Cognito Hosted UI and domain access
4. **Configure backend**: Use Terraform outputs for API configuration

See [api-implementation.md](./api-implementation.md) for backend integration steps.