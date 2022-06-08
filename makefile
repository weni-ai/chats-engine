dev_up:
	@docker-compose -f docker/docker-compose.yml up -d

dev_down:
	@docker-compose -f docker/docker-compose.yml down