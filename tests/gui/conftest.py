"""Existing GUI scenarios discard their disposable buffers during cleanup."""

import pytest


@pytest.fixture(autouse=True)
def discard_disposable_unsaved_buffers(monkeypatch):
    # Mock only the human answer, not the real document guard or filesystem.
    # Safety tests override this answer to exercise Save and Cancel as well.
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        "src.gui.app.QMessageBox.warning",
        lambda *args, **kwargs: QMessageBox.StandardButton.Discard,
    )
