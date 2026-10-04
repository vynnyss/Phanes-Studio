"""Compact numbered navigation for the two independent Studio histories."""
import gradio as gr

PAGE_BUTTONS = 7


def page_numbers(current, total):
    if total <= PAGE_BUTTONS:
        return list(range(1, total + 1))
    if current <= 4:
        return [1, 2, 3, 4, 5, "…", total]
    if current >= total - 3:
        return [1, "…", *range(total - 4, total + 1)]
    return [1, "…", current - 1, current, current + 1, "…", total]


def page_button_properties(current, total):
    numbers = page_numbers(current, total)
    properties = []
    for index in range(PAGE_BUTTONS):
        if index >= len(numbers):
            properties.append({
                "visible": False,
                "value": "",
                "interactive": False,
            })
            continue
        number = numbers[index]
        selected = number == current
        properties.append({
            "value": str(number),
            "visible": True,
            "interactive": isinstance(number, int) and not selected,
            "variant": "primary" if selected else "secondary",
        })
    return properties


def page_button_updates(current, total):
    return [
        gr.update(**properties)
        for properties in page_button_properties(current, total)
    ]


PAGINATION_CSS = """
.history-pagination {
    gap: 0 !important;
    flex-wrap: nowrap !important;
    border: 1px solid var(--border-color-primary, #48484f);
    border-radius: 999px;
    overflow: hidden;
    align-items: stretch;
}
.history-pagination > button {
    flex: 1 1 0 !important;
    min-width: 22px !important;
    margin: 0 !important;
    padding: 8px 4px !important;
    border: 0 !important;
    border-right: 1px solid var(--border-color-primary, #48484f) !important;
    border-radius: 0 !important;
    font-size: 12px !important;
    line-height: 20px !important;
    box-shadow: none !important;
}
.history-pagination > button:last-child {
    border-right: 0 !important;
}
.history-pagination > button.pager-edge {
    flex: 2.3 1 0 !important;
    min-width: 54px !important;
}
.history-pagination > button.primary:disabled {
    opacity: 1;
}
.history-pagination > button:focus-visible {
    outline: 2px solid var(--color-accent, #ff7a18);
    outline-offset: -3px;
}
"""
