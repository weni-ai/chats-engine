dev_up:
	@docker-compose -f docker/docker-compose.yml up -d database redis

dev_down:
	@docker-compose -f docker/docker-compose.yml down

add_initial_data:
	@python manage.py loaddata chats/fixtures/*.json