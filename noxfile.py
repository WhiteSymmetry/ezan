#!/usr/bin/env -S uv run --script
# /// script
dependencies = ["nox"]
# ///

import nox

# Nox versiyon gereksinimi
nox.needs_version = "2025.10.14"

# Varsayılan sanal ortam backend'i
nox.options.default_venv_backend = "uv"

# Varsayılan olarak çalıştırılacak oturumlar
nox.options.sessions = ["lint", "tests"]

# Test edilecek Python versiyonları
PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """
    Belirtilen tüm Python versiyonları için test paketini çalıştır.
    'nox -s tests-3.11' gibi komutlarla spesifik versiyonlar tetiklenebilir.
    """
    # Test bağımlılıklarını ve projeyi kur
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.install("-e", ".[test]")
    
    # Testleri kod kapsamı raporu ile çalıştır
    session.run("pytest", "--cov=ezan", "--cov-report=xml")


@nox.session(python="3.11")
def lint(session):
    """
    Kod stilini ve kalitesini kontrol etmek için linter'ları çalıştır.
    """
    # Linting araçlarını kur
    session.install("ruff")
    
    # Kod kontrolü ve format kontrolü yap
    session.run("ruff", "check", "ezan", "tests")
    session.run("ruff", "format", "--check", "ezan", "tests")


@nox.session(python="3.11")
def type_check(session):
    """
    Tip kontrolü çalıştır (opsiyonel).
    """
    session.install("mypy")
    session.install("-e", ".")
    session.run("mypy", "ezan")


@nox.session(python="3.11")
def security_check(session):
    """
    Güvenlik kontrolleri çalıştır (opsiyonel).
    """
    session.install("bandit", "safety")
    session.run("bandit", "-r", "ezan")
    session.run("safety", "check", "--file", "pyproject.toml")


if __name__ == "__main__":
    nox.main()
