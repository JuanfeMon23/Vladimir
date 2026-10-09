"""Ids ya creados durante la carga, por `code`, para resolver referencias."""

from dataclasses import dataclass, field


@dataclass
class Registry:
    staff: dict[str, str] = field(default_factory=dict)  # document_number -> id
    areas: dict[str, str] = field(default_factory=dict)
    samples: dict[str, str] = field(default_factory=dict)
    sample_types: dict[str, str] = field(default_factory=dict)
    preconditions: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    option_sets: dict[str, str] = field(default_factory=dict)
    options: dict[tuple[str, str], str] = field(default_factory=dict)
    analytes: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)  # code -> id catalogo
    label_versions: dict[str, str] = field(default_factory=dict)  # code -> v1 id
    templates: dict[str, str] = field(default_factory=dict)
    template_versions: dict[str, str] = field(default_factory=dict)
    consents: dict[str, str] = field(default_factory=dict)
    consent_versions: dict[str, str] = field(default_factory=dict)
    lab_tests: dict[str, str] = field(default_factory=dict)
