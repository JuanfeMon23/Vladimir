"""`error_responses`: errores de negocio declarados en el OpenAPI de forma DRY."""

from app.core.schemas import ErrorResponse, error_responses
from app.main import app


def test_error_responses_declares_the_error_model_per_status() -> None:
    responses = error_responses(404, 409)

    assert set(responses) == {404, 409}
    assert responses[404]["model"] is ErrorResponse
    assert responses[409]["model"] is ErrorResponse
    assert responses[404]["description"]


def test_error_responses_allows_overriding_a_description() -> None:
    responses = error_responses(409, descriptions={409: "version_in_use"})
    assert responses[409]["description"] == "version_in_use"


def _operations(method: str, suffix: str = "") -> dict[str, dict]:
    paths = app.openapi()["paths"]
    return {
        path: item[method]
        for path, item in paths.items()
        if method in item and path.endswith(suffix)
    }


def test_openapi_retire_routes_declare_version_in_use_409() -> None:
    retire = _operations("post", "/retire")
    assert len(retire) == 3  # print_labels, result_templates, consent_documents

    for operation in retire.values():
        response = operation["responses"]["409"]
        assert "version_in_use" in response["description"]
        schema = response["content"]["application/json"]["schema"]
        assert schema["$ref"].endswith("/ErrorResponse")


def test_openapi_every_patch_declares_404_409_and_422() -> None:
    for path, operation in _operations("patch").items():
        assert {"404", "409", "422"} <= set(operation["responses"]), path
