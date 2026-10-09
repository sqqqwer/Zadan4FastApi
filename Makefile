.PHONY: help install docker-up test format lint ruff check clean prepare

help:				## Все команды
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:			## Установить зависимости
	poetry install

docker-up:			## Поднять docker-compose
	docker-compose up -d

test:				## Тесты
	docker-compose -f docker-compose.test.yml up -d
	pytest -v

format:				## Только форматирование
	poetry run ruff format src

lint:				## Только проверка линтером с автофиксом
	poetry run ruff check src --fix

ruff:				## Ruff на всё сразу: форматирование + линт с автофиксом
	poetry run ruff format src
	poetry run ruff check src --fix

check:				## Проверка без изменений (для CI): формат + линт в режиме "только проверить"
	poetry run ruff format src --check
	poetry run ruff check src

clean:				## Удалить кэши
	find . -type d \( -name '__pycache__' -o -name '.ruff_cache' -o -name '.pytest_cache' -o -name '.mypy_cache' \) -prune -exec rm -rf {} +

prepare:	## Проверка линтером с автофиксом + форматирование + тесты + очистка кэша
	make ruff
	make test
	make clean
