from dataclasses import dataclass
import bpy
from .draw import GuideDraw


draw_handlers = []


@dataclass
class Handle:
    """Common functions for the handle data."""

    handle: int | None = None

    def remove(self):
        """Remove the draw handler."""
        if self.handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, "WINDOW")
            if self.handle in draw_handlers:
                draw_handlers.remove(self.handle)


@dataclass
class Guide(Handle):
    """Dataclass for the guide draw handler."""

    callback: GuideDraw | None = None

    def create(self, context):
        """Create a guide draw handler."""
        self.callback = GuideDraw()
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
            self.callback.draw, (context,), "WINDOW", "POST_VIEW"
        )
        draw_handlers.append(self.handle)


@dataclass
class Common:
    """Common functions for the handle data."""

    def clear(self):
        """Remove all draw handlers on this instance."""
        for handle in vars(self).values():
            handle.remove()

    def clear_all(self):
        """Remove all draw handlers from global registry."""
        for handle in draw_handlers:
            bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
        draw_handlers.clear()
