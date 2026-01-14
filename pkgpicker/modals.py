from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

class ConfirmModal(ModalScreen[bool]):
    def __init__(self, title: str, body: str):
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[b]{self._title}[/b]"),
            Static(self._body),
            Horizontal(
                Button("Abbrechen", id="no", variant="error"),
                Button("OK", id="yes", variant="success"),
            ),
            id="modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

class OutputModal(ModalScreen[None]):
    def __init__(self, title: str, body: str):
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[b]{self._title}[/b]"),
            Static(self._body),
            Button("Schließen", id="close", variant="primary"),
            id="modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

class TextInputModal(ModalScreen[str]):
    def __init__(self, title: str, placeholder: str):
        super().__init__()
        self._title = title
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[b]{self._title}[/b]"),
            Input(placeholder=self._placeholder, id="ti"),
            Horizontal(
                Button("OK", id="ok", variant="success"),
                Button("Cancel", id="cancel", variant="error"),
            ),
            id="modal",
        )

    def on_mount(self) -> None:
        self.query_one("#ti", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss("")
        else:
            self.dismiss(self.query_one("#ti", Input).value.strip())

