from sqlalchemy.orm import Session

from app.models.db import Problem, ProblemSolution, Quest


class ProblemRepository:
    """Repository for problem queries."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, problem_id: int) -> Problem | None:
        return self.db.query(Problem).filter(Problem.id == problem_id).first()

    def get_all(self, limit: int | None = None) -> list[Problem]:
        query = self.db.query(Problem)
        if limit:
            query = query.limit(limit)
        return query.all()

    def get_by_difficulty(self, difficulty: str) -> list[Problem]:
        return self.db.query(Problem).filter(Problem.difficulty == difficulty).all()

    def list_problems(
        self,
        page: int,
        limit: int,
        category: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Problem], int]:
        query = self.db.query(Problem)
        if category:
            query = query.filter(Problem.category == category)
        if search:
            query = query.filter(Problem.title.ilike(f"%{search}%"))

        total = query.count()
        problems = (
            query.order_by(Problem.id).offset((page - 1) * limit).limit(limit).all()
        )
        return problems, total

    def get_problem_ids_with_quests(self, problem_ids: list[int]) -> set[int]:
        return set(
            q.problem_id
            for q in self.db.query(Quest.problem_id)
            .filter(Quest.problem_id.in_(problem_ids))
            .all()
        )

    def get_solution_by_problem_id(self, problem_id: int) -> ProblemSolution | None:
        return (
            self.db.query(ProblemSolution)
            .filter(ProblemSolution.problem_id == problem_id)
            .first()
        )

    def save_solution(self, problem_id: int, solution: str) -> ProblemSolution:
        new_solution = ProblemSolution(problem_id=problem_id, solution=solution)
        self.db.add(new_solution)
        self.db.commit()
        self.db.refresh(new_solution)
        return new_solution
