# what is this

yeah i'm not sure either, but i'm gonna build it anyway.

# cleanup etc

```bash
poetry run black .
poetry run isort .
poetry run vulture ccrepe --min-confidence 90
poetry run mypy .
poetry run pytest
```