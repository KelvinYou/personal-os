class NutritionDataError(Exception):
    """Raised for any dataset defect: unknown id, missing price, illegal
    unit/basis, or a piece/serving ingredient that can't be converted to
    grams. Never guessed around; see the nutrition source contract."""


class NutritionSourceMissing(NutritionDataError):
    """Raised when repos/notes/datasets/nutrition isn't checked out.

    notes is a public repo — anyone with `git clone --recursive` gets it, so
    unlike data/ (owner's private repository) there is no graceful-fallback path here.
    """
