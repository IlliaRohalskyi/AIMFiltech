lint:
	pylint src test

format:
	@echo "Running black..."
	@black .
	@echo "Running isort..."
	@isort .
	@echo "Formatting complete!"

test:
	pytest

# Deploy everything (build image, push to ECR, terraform apply)
deploy:
	./deploy.sh | tee .last_deploy.log

destroy:
	@echo "🔥 Destroying infrastructure..."
	@cd terraform && \
	AWS_ACCOUNT_ID=$$(aws sts get-caller-identity --query Account --output text) && \
	terraform destroy -auto-approve \
		-var="image_tag="
	cd ..
	@echo "✅ Infrastructure destroyed successfully!"

pip-export:
	uv export --format requirements-txt > requirements.txt
	@echo "✅ requirements.txt generated successfully!"

# Helper: Show last image tag used
last-tag:
	@grep 'ECR:' .last_deploy.log | awk -F: '{print $$4}' | sed 's/ //g'


.PHONY: lint format test deploy destroy