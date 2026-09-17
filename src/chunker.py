import re

class Chunker:
    """Cuts text into chunks, choosing a strategy per file type."""

    def __init__(self, supported_suffixes: set[str]) -> None:
        known_strategies = {
            ".py": self._split_python,
            ".md": self._split_markdown,
        }
        self._strategies = {
            suffix: known_strategies.get(suffix, self._split_generic)
            for suffix in supported_suffixes
        }

    def split_text(
        self,
        text: str,
        max_chunk_size: int,
        suffix: str,
    ) -> list[tuple[int, int]]:
        """Return (start, end) character spans covering the whole text."""
        strategy = self._strategies.get(suffix, self._split_generic)
        return strategy(text, max_chunk_size)

    def _split_generic(self, text: str, max_chunk_size: int) -> list[tuple[int, int]]:
        """Fallback: cut every max_chunk_size characters."""
        spans = []
        start = 0
        while start < len(text):
            end = min(start + max_chunk_size, len(text))
            spans.append((start, end))
            start = end
        return spans

    # def _split_markdown(self, text: str, max_chunk_size: int) -> list[tuple[int, int]]:
    #     """Split by paragraphs: never cut a paragraph in half."""
    #     spans = []
    #     start = 0
    #     while start < len(text):
    #         end = min(start + max_chunk_size, len(text))
    #         if end < len(text):
    #             boundary = text.rfind("\n\n", start, end)
    #             if boundary > start:
    #                 end = boundary
    #         spans.append((start, end))
    #         start = end
    #     return spans

    def _split_markdown(
        self,
        text: str,
        max_chunk_size: int,
    ) -> list[tuple[int, int]]:
        """Split Markdown at paragraph boundaries when possible.

        The method first tries to split at the last separator containing
        two or more line breaks. If no separator exists before the size
        limit, it cuts exactly at ``max_chunk_size``.

        Args:
            text: Markdown text to split.
            max_chunk_size: Maximum number of characters per chunk.

        Returns:
            A list of ``(start, end)`` character ranges.
        """
        spans = []
        start = 0

        while start < len(text):
            end = min(start + max_chunk_size, len(text))

            if end < len(text):
                boundary = self._find_last_blank_line(
                    text,
                    start,
                    end,
                )

                if boundary > start:
                    end = boundary

            spans.append((start, end))
            start = end

        return spans

    # def _split_python(self, text: str, max_chunk_size: int) -> list[tuple[int, int]]:
    #     """Split by lines, preferring blank lines between functions."""
    #     spans = []
    #     start = 0
    #     while start < len(text):
    #         end = min(start + max_chunk_size, len(text))
    #         if end < len(text):
    #             boundary = text.rfind("\n\n", start, end)
    #             if boundary <= start:
    #                 boundary = text.rfind("\n", start, end)
    #             if boundary > start:
    #                 end = boundary
    #         spans.append((start, end))
    #         start = end
    #     return spans

    def _split_python(
        self,
        text: str,
        max_chunk_size: int,
    ) -> list[tuple[int, int]]:
        """Split Python code at blank-line boundaries when possible.

        The method first tries to split at a separator containing two or
        more line breaks. If no such separator exists, it tries to split
        at the last individual line break before the size limit.

        Args:
            text: Python source code to split.
            max_chunk_size: Maximum number of characters per chunk.

        Returns:
            A list of ``(start, end)`` character ranges.
        """
        spans = []
        start = 0

        while start < len(text):
            end = min(start + max_chunk_size, len(text))

            if end < len(text):
                boundary = self._find_last_blank_line(
                    text,
                    start,
                    end,
                )

                if boundary <= start:
                    boundary = text.rfind("\n", start, end)

                if boundary > start:
                    end = boundary

            spans.append((start, end))
            start = end

        return spans

    @staticmethod
    def _find_last_blank_line(
        text: str,
        start: int,
        end: int,
    ) -> int:
        """Find the end of the last separator with two or more line breaks.
        A separator can contain spaces or tabs between line breaks.
        For example: ``\\n\\n``, ``\\n\\n\\n``, ``\\n \\n`` or ``\\n\\t\\n``.
        Args:
            text: Complete text being split.
            start: Start of the current search area.
            end: End of the current search area.
        Returns:
            The position immediately after the last separator, or -1 if
            no separator was found.
        """
        section = text[start:end]
        last_boundary = -1

        for match in re.finditer(r"\n(?:[ \t]*\n)+", section):
            last_boundary = start + match.end()

        return last_boundary
