"""Render prompt templates by substituting placeholders."""

from .templates import PromptTemplates


def render_prompt(template_name: str, **kwargs) -> str:
    """Render a named prompt template with the given keyword arguments.

    Args:
        template_name: Attribute name on PromptTemplates (e.g. 'BULL_CASE').
        **kwargs: Placeholder values — keys should match {PLACEHOLDER} names
                  in the template (case-sensitive).

    Returns:
        The rendered prompt string.

    Raises:
        AttributeError: If template_name does not exist.
        KeyError: If a required placeholder is missing from kwargs.
    """
    template = getattr(PromptTemplates, template_name)
    return template.format(**kwargs)


def list_templates() -> list[str]:
    """Return the names of all available prompt templates."""
    return [
        attr
        for attr in dir(PromptTemplates)
        if not attr.startswith("_") and isinstance(getattr(PromptTemplates, attr), str)
    ]
