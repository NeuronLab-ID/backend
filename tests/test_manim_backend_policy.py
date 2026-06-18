from fastapi import HTTPException


def test_backend_policy_defaults_to_cpu_and_includes_unavailable_egpu(monkeypatch):
    import app.services.manim_backends as backends

    monkeypatch.setattr(backends, "MANIM_EGPU_ENABLED", False)
    monkeypatch.setattr(backends, "MANIM_DEFAULT_BACKEND", "cpu")

    policies = backends.list_manim_backend_policies()

    assert [policy.name for policy in policies] == ["cpu", "egpu"]
    assert policies[0].available is True
    assert policies[0].default is True
    assert policies[1].available is False
    assert policies[1].reason == "eGPU backend is disabled by policy"


def test_queue_list_backends_exposes_unavailable_egpu(monkeypatch):
    from unittest.mock import MagicMock

    import app.services.manim_queue as queue_module
    from app.services.manim_backends import ManimBackendPolicy

    monkeypatch.setattr(
        queue_module,
        "list_manim_backend_policies",
        lambda: [
            ManimBackendPolicy(name="cpu", available=True, default=True),
            ManimBackendPolicy(
                name="egpu",
                available=False,
                default=False,
                reason="eGPU backend is disabled by policy",
            ),
        ],
    )

    result = queue_module.ManimQueueService(MagicMock()).list_backends()

    assert result["default_backend"] == "cpu"
    assert [backend["name"] for backend in result["backends"]] == ["cpu", "egpu"]
    egpu = result["backends"][1]
    assert egpu["available"] is False
    assert egpu["reason"] == "eGPU backend is disabled by policy"


def test_egpu_policy_uses_only_allowlisted_existing_device(monkeypatch, tmp_path):
    import app.services.manim_backends as backends

    fake_dri = tmp_path / "dri"
    fake_dri.mkdir()
    monkeypatch.setattr(backends, "MANIM_EGPU_ENABLED", True)
    monkeypatch.setattr(backends, "MANIM_DEFAULT_BACKEND", "egpu")
    monkeypatch.setattr(backends, "MANIM_EGPU_DEVICE_PATHS", (str(fake_dri), "/dev/not-allowed"))
    monkeypatch.setattr(backends, "_ALLOWED_EGPU_DEVICE_PATHS", {str(fake_dri)})

    policy = backends.get_manim_backend_policy("egpu")

    assert policy.name == "egpu"
    assert policy.default is True
    assert policy.docker_kwargs() == {"devices": [f"{fake_dri}:{fake_dri}:rwm"]}


def test_unavailable_egpu_rejected(monkeypatch):
    import app.services.manim_backends as backends

    monkeypatch.setattr(backends, "MANIM_EGPU_ENABLED", True)
    monkeypatch.setattr(backends, "MANIM_EGPU_DEVICE_PATHS", ("/dev/dri",))
    monkeypatch.setattr(backends.Path, "exists", lambda self: False)

    try:
        backends.get_manim_backend_policy("egpu")
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("expected HTTPException")


def test_cuda_backend_is_not_accepted():
    import app.services.manim_backends as backends

    try:
        backends.get_manim_backend_policy("cuda")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "cpu" in str(exc.detail) and "egpu" in str(exc.detail)
    else:
        raise AssertionError("expected HTTPException")
