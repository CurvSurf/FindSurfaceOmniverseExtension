import math

import omni.ui as ui


class BorderedGroupView:
    """A fieldset-like omni.ui group with a title gap in the top border."""

    DEFAULT_PADDING = 10
    DEFAULT_LABEL_HEIGHT = 18
    DEFAULT_TITLE_X = 14
    DEFAULT_TITLE_GAP_PADDING = 8
    DEFAULT_ROW_HEIGHT = 28
    DEFAULT_ROW_SPACING = 6
    DEFAULT_BORDER_COLOR = 0xFFE6E6E6
    DEFAULT_TITLE_COLOR = 0xFFEDEDED
    DEFAULT_TITLE_FONT_SIZE = 13

    def __init__(
        self,
        title,
        *,
        row_count=None,
        row_heights=None,
        height=None,
        padding=DEFAULT_PADDING,
        label_height=DEFAULT_LABEL_HEIGHT,
        title_x=DEFAULT_TITLE_X,
        title_gap_padding=DEFAULT_TITLE_GAP_PADDING,
        row_height=DEFAULT_ROW_HEIGHT,
        row_spacing=DEFAULT_ROW_SPACING,
        border_color=DEFAULT_BORDER_COLOR,
        title_color=DEFAULT_TITLE_COLOR,
        title_font_size=DEFAULT_TITLE_FONT_SIZE,
        ui_module=ui,
    ):
        self.title = str(title)
        self.row_count = row_count
        self.row_heights = tuple(row_heights) if row_heights is not None else None
        self.explicit_height = height
        self.padding = padding
        self.label_height = label_height
        self.title_x = title_x
        self.title_gap_padding = title_gap_padding
        self.row_height = row_height
        self.row_spacing = row_spacing
        self.border_color = border_color
        self.title_color = title_color
        self.title_font_size = title_font_size
        self.ui = ui_module
        self._contexts = []

    def __enter__(self):
        zstack_cls = getattr(self.ui, "ZStack", None)
        if zstack_cls is None:
            self.ui.Label(self.title, height=self.label_height)
            content_ctx = self.ui.VStack(spacing=self.row_spacing)
            content_ctx.__enter__()
            self._contexts.append(content_ctx)
            return self

        height = self._height()
        content_height = self._content_height()
        title_width = self._title_text_width(self.title)
        title_gap_x = max(0, self.title_x - self.title_gap_padding)
        title_gap_width = title_width + self.title_gap_padding * 2

        zstack_ctx = zstack_cls(height=height)
        zstack_ctx.__enter__()
        self._contexts.append(zstack_ctx)
        self._build_border(height, title_gap_x, title_gap_width)

        outer_ctx = self.ui.VStack(height=height, spacing=0)
        outer_ctx.__enter__()
        self._contexts.append(outer_ctx)
        self.ui.Spacer(height=self._content_top())

        row_ctx = self.ui.HStack(height=content_height, spacing=0)
        row_ctx.__enter__()
        self._contexts.append(row_ctx)
        self.ui.Spacer(width=self.padding)

        content_ctx = self.ui.VStack(height=content_height, spacing=self.row_spacing)
        content_ctx.__enter__()
        self._contexts.append(content_ctx)
        return self

    def __exit__(self, exc_type, exc, tb):
        if not self._contexts:
            return False

        content_ctx = self._contexts.pop()
        content_ctx.__exit__(exc_type, exc, tb)

        if len(self._contexts) >= 3:
            self.ui.Spacer(width=self.padding)
            row_ctx = self._contexts.pop()
            row_ctx.__exit__(exc_type, exc, tb)

            outer_ctx = self._contexts.pop()
            outer_ctx.__exit__(exc_type, exc, tb)

            self._build_title()

        while self._contexts:
            self._contexts.pop().__exit__(exc_type, exc, tb)
        return False

    def _row_heights(self):
        if self.row_heights is not None:
            return self.row_heights
        count = self.row_count if self.row_count is not None else 1
        return tuple(self.row_height for _ in range(max(0, int(count))))

    def _height(self):
        if self.explicit_height is not None:
            return self.explicit_height
        return self._content_top() + self._content_height() + self.padding

    def _content_top(self):
        return self.label_height // 2 + self.padding

    def _content_height(self):
        if self.explicit_height is not None and self.row_heights is None and self.row_count is None:
            return max(0, self.explicit_height - self._content_top() - self.padding)
        row_heights = self._row_heights()
        if not row_heights:
            return 0
        return sum(row_heights) + self.row_spacing * (len(row_heights) - 1)

    def _build_border(self, height, title_gap_x, title_gap_width):
        rectangle_cls = getattr(self.ui, "Rectangle", None)
        if rectangle_cls is None:
            return

        line_style = self._border_line_style()
        border_top = self.label_height // 2
        border_height = max(1, height - border_top)
        side_height = max(1, border_height - 2)
        with self.ui.VStack(height=height, spacing=0):
            self.ui.Spacer(height=border_top)
            with self.ui.HStack(height=1, spacing=0):
                if title_gap_x > 0:
                    rectangle_cls(width=title_gap_x, height=1, style=line_style)
                self.ui.Spacer(width=title_gap_width)
                rectangle_cls(height=1, style=line_style)
            with self.ui.HStack(height=side_height, spacing=0):
                rectangle_cls(width=1, style=line_style)
                self.ui.Spacer()
                rectangle_cls(width=1, style=line_style)
            rectangle_cls(height=1, style=line_style)

    def _build_title(self):
        title_width = self._title_text_width(self.title)
        placer_cls = getattr(self.ui, "Placer", None)
        if placer_cls:
            with placer_cls(offset_x=self.title_x, offset_y=0):
                self._title_text(title_width)
            return
        with self.ui.HStack(height=self.label_height, spacing=0):
            self.ui.Spacer(width=self.title_x)
            self._title_text(title_width)
            self.ui.Spacer()

    def _title_text(self, width):
        self.ui.Label(
            self.title,
            width=width,
            height=self.label_height,
            style={"color": self.title_color, "font_size": self.title_font_size},
        )

    def _border_line_style(self):
        return {"background_color": self.border_color, "border_width": 0}

    @staticmethod
    def _title_text_width(title):
        width = 0
        for char in str(title):
            if char == " ":
                width += 4
            elif char in "ilI.,'`|!:":
                width += 4
            elif char in "mwMW@#%&":
                width += 10
            elif char.isupper():
                width += 8
            else:
                width += 7
        return max(1, math.ceil(width + 2))


__all__ = ["BorderedGroupView"]
