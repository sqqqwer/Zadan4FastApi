import datetime
from uuid import UUID

JWT_ACCESS_TOKEN = "test-access-token"
COMPANY_ID = UUID("250d622b-2a03-43c4-aac7-e553965e28f0")
DIFFERRNT_COMPANY_ID = UUID("e8e8861c-eff4-4ac6-8446-4fb135e80cc3")
CURRENT_USER_ID = UUID("d3417974-cf31-469c-855e-110f99590638")

TITLE = "test title"
DESCRIPTION = "test description"
DEADLINE = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)
ESTIMATED_MINUTES = 1111
RESPONSIBLE_ID = UUID("149bbcd7-0448-4c9e-8ec4-423125f71ef8")
OBSERVER_IDS = [
    UUID("b35ca594-dfcc-46e5-b65a-dff89c75b16e"),
    UUID("bb07d5e4-ded4-48a8-ba07-0bc7fa18376d"),
]
EXECUTOR_IDS = [
    UUID("f999d91d-6b2c-4405-8c9e-271b7edbb1e5"),
    UUID("08ecd0b1-60f2-4aba-89f1-de4f3113b6e8"),
]

UPDATED_TITLE = "test title"
UPDATED_DESCRIPTION = "test description"
UPDATED_DEADLINE = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=4)
UPDATED_ESTIMATED_MINUTES = 2222
UPDATED_RESPONSIBLE_ID = UUID("3b1bb17d-8666-42f1-a043-0a31ff238fd0")
UPDATED_OBSERVER_IDS = [
    UUID("ba4b4793-9e4b-4bf7-a1bf-9d1a018d7f0e"),
    UUID("2d08f711-6431-4314-bc81-6df6e7828ee6"),
]
UPDATED_EXECUTOR_IDS = [
    UUID("9c63fd51-227b-4d0b-8a4a-5bf7003c3797"),
    UUID("20cd27b1-a048-42aa-aaa8-12bf6f6b3736"),
]
