"""Punto unico de registro de modelos para Alembic (autogenerate).

Registrar un modulo nuevo = importar su `models.py` aca. `env.py` importa
este archivo (y por lo tanto `Base`) para que `Base.metadata` conozca todas
las tablas del proyecto.
"""

from app.core.db import activity as core_activity_models  # noqa: F401
from app.core.db.base import Base
from app.modules.consent_documents import (
    models as consent_documents_models,  # noqa: F401
)
from app.modules.lab_areas import models as lab_areas_models  # noqa: F401
from app.modules.lab_tests import models as lab_tests_models  # noqa: F401
from app.modules.preconditions import models as preconditions_models  # noqa: F401
from app.modules.print_labels import models as print_labels_models  # noqa: F401
from app.modules.result_templates import models as result_templates_models  # noqa: F401
from app.modules.samples import models as samples_models  # noqa: F401
from app.modules.staff import models as staff_models  # noqa: F401

__all__ = ["Base"]
