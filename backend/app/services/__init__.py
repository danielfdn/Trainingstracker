"""Fachlogik, die ueber reines CRUD hinausgeht.

Die Router bleiben duenn, solange eine Operation nur einen Datensatz liest
oder schreibt. Sobald etwas gerechnet wird oder mehrere Repos beteiligt
sind - wie beim Monatsvergleich des Trainingslogs - gehoert es hierher.
"""

from app.services.training_log import TrainingLogService

__all__ = ["TrainingLogService"]
