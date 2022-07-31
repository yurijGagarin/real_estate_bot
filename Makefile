setup:
	pip install -r requirements.txt
run:
	python main.py
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
