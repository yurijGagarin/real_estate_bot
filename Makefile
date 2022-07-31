setup:
	pip install -r requirements.txt
run:
	python -m bot.main
db-autogenerate:
	alembic revision --autogenerate
db-up:
	alembic upgrade head
db-down:
	alembic downgrade -1
db-redo:
	alembic downgrade -1 && alembic upgrade head
deploy:
	./server-tools.sh deploy
