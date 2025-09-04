# Infrastructure - Terraform

Infrastructure as Code (IaC) for the Play Later application using Terraform.

## 🏗️ Architecture

- **Platform**: Cloud-agnostic Terraform configuration
- **Tool**: Terraform for infrastructure provisioning and management
- **Structure**: Modular configuration with variables, outputs, and main resources

## 🚀 Quick Start

### Prerequisites

- Terraform CLI installed
- Cloud provider CLI configured (AWS CLI, Azure CLI, or gcloud)
- Appropriate cloud provider credentials

### Setup

```bash
# Navigate to infrastructure directory
cd infra/

# Initialize Terraform
terraform init

# Format Terraform files
terraform fmt -recursive .

# Validate configuration
terraform validate

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply
```

## 📁 Project Structure

```
infra/
├── main.tf         # Main infrastructure resources
├── variables.tf    # Input variables
├── outputs.tf      # Output values
├── terraform.tf    # Terraform configuration (optional)
├── providers.tf    # Provider configurations (optional)
└── README.md       # This file
```

## 🛠️ Configuration Files

### main.tf
Contains the primary infrastructure resources and configurations.

### variables.tf
Defines input variables for the Terraform configuration:
- Environment settings
- Resource naming
- Configuration parameters

### outputs.tf
Defines output values that can be used by other Terraform configurations or displayed after apply.

## 🔧 Development Workflow

### Formatting
```bash
# Format all Terraform files recursively
terraform fmt -recursive infra/
```

### Validation
```bash
# Validate Terraform configuration
terraform validate
```

### Planning
```bash
# Review planned changes before applying
terraform plan
```

### Applying Changes
```bash
# Apply infrastructure changes
terraform apply

# Auto-approve for automation (use with caution)
terraform apply -auto-approve
```

### Destroying Resources
```bash
# Destroy all managed infrastructure (use with extreme caution)
terraform destroy
```

## 📋 Best Practices

### Code Style
- Use consistent naming conventions
- Add meaningful comments for complex resources
- Use variables for configurable values
- Define outputs for important resource attributes

### Security
- Never commit sensitive values to version control
- Use Terraform variables or external systems for secrets
- Apply least-privilege access policies
- Enable encryption at rest and in transit

### State Management
- Use remote state backends for team collaboration
- Enable state locking to prevent concurrent modifications
- Backup state files regularly
- Use workspaces for environment separation

## 🔒 Environment Variables

Common environment variables for cloud providers:

### AWS
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"
```

### Azure
```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
```

### Google Cloud
```bash
export GOOGLE_CREDENTIALS="path/to/service-account.json"
export GOOGLE_PROJECT="your-project-id"
export GOOGLE_REGION="us-central1"
```

## 🚀 Deployment

### Development Environment
```bash
terraform workspace select development
terraform plan -var-file="dev.tfvars"
terraform apply -var-file="dev.tfvars"
```

### Production Environment
```bash
terraform workspace select production
terraform plan -var-file="prod.tfvars"
terraform apply -var-file="prod.tfvars"
```

## 📊 Monitoring and Maintenance

- Monitor resource costs and usage
- Review security groups and access policies regularly
- Update Terraform and provider versions
- Document infrastructure changes in commit messages
- Implement backup and disaster recovery procedures

## 🐛 Troubleshooting

### Common Issues

1. **State Lock Errors**: Check for existing locks and force-unlock if necessary
2. **Provider Version Conflicts**: Pin provider versions in configuration
3. **Resource Dependencies**: Use `depends_on` for explicit dependencies
4. **Credential Issues**: Verify cloud provider authentication

### Debug Mode
```bash
# Enable detailed logging
export TF_LOG=DEBUG
terraform apply
```

### State Recovery
```bash
# Import existing resources
terraform import aws_instance.example i-1234567890abcdef0

# Remove resources from state without destroying
terraform state rm aws_instance.example
```

## 📚 Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [Cloud Provider Terraform Guides](https://learn.hashicorp.com/terraform)

## 🔄 CI/CD Integration

This infrastructure configuration is designed to work with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
name: Terraform
on: [push, pull_request]
jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: hashicorp/setup-terraform@v1
      - run: terraform fmt -check -recursive infra/
      - run: terraform init
      - run: terraform validate
      - run: terraform plan
```