"""Acceso a las dos versiones ya analizadas de un proyecto de Ghidra."""

from __future__ import annotations

import atexit
from pathlib import Path
from typing import Any, Literal, Self

Version = Literal["old", "new"]


class GhidraSession:
    """Singleton por proceso: open abre old/new y close libera sus recursos.

    Compartido por los sets en el bucle secuencial del agente. No admite
    abrir/cerrar concurrentemente ni mantiene varias comparaciones a la vez.
    """

    _instance = None

    def __new__(cls: type[Self]) -> Self:
        """Obtener la instancia compartida sin reinicializar una sesión existente."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.old = instance.new = None
            instance.flat_old = instance.flat_new = None
            instance._project = None
            instance._consumer_old = instance._consumer_new = None
            cls._instance = instance
        return cls._instance

    def open(
        self,
        project_file: str | Path,
        program_old: str,
        program_new: str,
        install_dir: str | Path | None = None,
    ) -> Self:
        """Abrir el .gpr y dos rutas internas; devolver la sesión y limpiar si falla."""
        if self._project is not None:
            raise RuntimeError("La sesión ya está abierta. Usa la existente o llama a close().")

        project_file = Path(project_file).resolve()

        if not project_file.is_file():
            raise FileNotFoundError(project_file)

        import pyghidra

        if not pyghidra.started():
            pyghidra.start(install_dir=install_dir)

        # Clase Java cargada en ejecución
        from ghidra.program.flatapi import FlatProgramAPI  # pyright: ignore[reportMissingImports]

        try:
            self._project = pyghidra.open_project(
                str(project_file.parent), project_file.stem
            )
            self.old, self._consumer_old = pyghidra.consume_program(
                self._project, program_old
            )
            self.new, self._consumer_new = pyghidra.consume_program(
                self._project, program_new
            )
            self.flat_old = FlatProgramAPI(self.old)
            self.flat_new = FlatProgramAPI(self.new)
        except Exception:
            self.close()
            raise

        # Registrado después del arranque de Java para cerrar antes que la JVM.
        atexit.register(self.close)

        return self

    def __getitem__(self, version: Version) -> Any:
        """Obtener el Program Java mediante session['old'] o session['new']."""
        if self.old is None or self.new is None:
            raise RuntimeError("Inicializa la sesión con session.open(...).")
        return {"old": self.old, "new": self.new}[version]

    def close(self) -> None:
        """Liberar new, old y proyecto; permitir llamadas repetidas y posterior reapertura."""
        atexit.unregister(self.close)
        try:
            try:
                if self.new is not None:
                    self.new.release(self._consumer_new)
            finally:
                try:
                    if self.old is not None:
                        self.old.release(self._consumer_old)
                finally:
                    if self._project is not None:
                        self._project.close()
        finally:
            self.old = self.new = None
            self.flat_old = self.flat_new = None
            self._project = None
            self._consumer_old = self._consumer_new = None


session = GhidraSession()
