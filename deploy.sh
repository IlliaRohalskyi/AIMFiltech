#!/bin/bash
set -euo pipefail

AWS_REGION="eu-central-1"
TF_DIR="terraform"
TF_VAR_FILE="$TF_DIR/terraform.tfvars"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD)"

# 1. Create ECR repos only (so we can push images)
cd "$TF_DIR"
terraform init

# Only create ECR repos so images can be pushed 
terraform apply -auto-approve \
  -target=module.pipelines_storage.aws_ecr_repository.lambda_ecr_repo \
  -target=module.pipelines_storage.aws_ecr_repository.openfoam_ecr_repo \
  -target=module.pipelines_storage.aws_ecr_repository.sagemaker_ecr_repo \
  -var="image_tag="

# Get ECR repo URLs from Terraform outputs
LAMBDA_ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/lambda-ecr-repo"
OPENFOAM_ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/openfoam-ecr-repo"
SAGEMAKER_ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/sagemaker-ecr-repo"

if terraform output -raw lambda_ecr_repo_url > /dev/null 2>&1; then
  LAMBDA_ECR_REPO=$(terraform output -raw lambda_ecr_repo_url)
fi
if terraform output -raw openfoam_ecr_repo_url > /dev/null 2>&1; then
  OPENFOAM_ECR_REPO=$(terraform output -raw openfoam_ecr_repo_url)
fi
if terraform output -raw sagemaker_ecr_repo_url > /dev/null 2>&1; then
  SAGEMAKER_ECR_REPO=$(terraform output -raw sagemaker_ecr_repo_url)
fi
cd ..

echo "LAMBDA_ECR_REPO: $LAMBDA_ECR_REPO"
echo "OPENFOAM_ECR_REPO: $OPENFOAM_ECR_REPO"
echo "SAGEMAKER_ECR_REPO: $SAGEMAKER_ECR_REPO"

# 2. Build and push all three images
echo "🐳 Building and pushing Lambda image..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$LAMBDA_ECR_REPO"
docker build -f Dockerfile.lambda -t "$LAMBDA_ECR_REPO:$IMAGE_TAG" .
docker push "$LAMBDA_ECR_REPO:$IMAGE_TAG"

echo "🐳 Building and pushing OpenFOAM image..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$OPENFOAM_ECR_REPO"
docker build -f Dockerfile.openfoam -t "$OPENFOAM_ECR_REPO:$IMAGE_TAG" .
docker push "$OPENFOAM_ECR_REPO:$IMAGE_TAG"

echo "🐳 Building and pushing SageMaker image..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$SAGEMAKER_ECR_REPO"
docker build -f Dockerfile.sagemaker -t "$SAGEMAKER_ECR_REPO:$IMAGE_TAG" .
docker push "$SAGEMAKER_ECR_REPO:$IMAGE_TAG"

echo ""
echo "✅ Lambda image:     $LAMBDA_ECR_REPO:$IMAGE_TAG"
echo "✅ OpenFOAM image:   $OPENFOAM_ECR_REPO:$IMAGE_TAG"
echo "✅ SageMaker image:  $SAGEMAKER_ECR_REPO:$IMAGE_TAG"

# 3. Run full Terraform apply to deploy everything, passing in image tag for referencing in Lambda/ECS/SageMaker
cd "$TF_DIR"
terraform apply -auto-approve -var="image_tag=$IMAGE_TAG"
cd ..

echo ""
echo "🚀 ALL DONE! Infrastructure and all images deployed."
echo "🔬 Lambda/ECS/SageMaker should be running the new images."
echo "📦 Images are tagged with: $IMAGE_TAG"
echo ""
echo "📋 Deployment Summary:"
echo "   - Lambda ECR:     $LAMBDA_ECR_REPO:$IMAGE_TAG"
echo "   - OpenFOAM ECR:   $OPENFOAM_ECR_REPO:$IMAGE_TAG"
echo "   - SageMaker ECR:  $SAGEMAKER_ECR_REPO:$IMAGE_TAG"