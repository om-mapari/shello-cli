"""Custom Markdown renderer with enhanced code block display"""
from rich.markdown import Markdown, CodeBlock, Heading
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.console import Group


class CustomCodeBlock(CodeBlock):
    """Custom code block with copy hint"""
    
    def __rich_console__(self, console, options):
        code = str(self.text).rstrip()
        
        # Create syntax highlighted code
        syntax = Syntax(
            code,
            self.lexer_name,
            theme=self.theme,
            word_wrap=False,
            padding=0,
        )
        
        # Create hint text
        hint = Text()
        hint.append("💡 ", style="yellow")
        hint.append("Tip: Select text to copy", style="dim italic")
        
        # Combine code and hint
        yield Panel(
            Group(syntax, hint),
            border_style="blue",
            padding=(0, 1),
            expand=False
        )


class LeftAlignedHeading(Heading):
    """Custom heading with left alignment"""
    
    def __rich_console__(self, console, options):
        text = self.text
        text.justify = "left"
        yield text


class EnhancedMarkdown(Markdown):
    """Enhanced Markdown with custom code block rendering and left-aligned headings"""
    
    elements = {
        **Markdown.elements,
        "code_block": CustomCodeBlock,
        "heading_open": LeftAlignedHeading,
    }
