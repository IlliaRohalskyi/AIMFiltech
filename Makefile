lint:
	pylint src test

format:
	@echo "Running black..."
	@black .
	@echo "Running isort..."
	@isort .
	@echo "Formatting complete!"

test:
	pytest test

# Deploy everything (build image, push to ECR, terraform apply)
deploy:
	./deploy.sh | tee .last_deploy.log

# Helper: Show last image tag used
last-tag:
	@grep 'ECR:' .last_deploy.log | awk -F: '{print $$4}' | sed 's/ //g'


.PHONY: lint format test deploy