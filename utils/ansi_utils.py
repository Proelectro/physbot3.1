TEXT_COLORS = {
    'gray': 30, 'grey': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'pink': 35, 'magenta': 35,
    'cyan': 36,
    'white': 37,
    'default': 39,
}

# Dictionary mapping color names to ANSI background codes
BACKGROUND_COLORS = {
    'firefly_dark_blue': 40,
    'orange': 41,
    'marble_blue': 42,
    'greyish_turquoise': 43,
    'gray': 44, 'grey': 44,
    'indigo': 45,
    'light_gray': 46,
    'white': 47,
    'default': 49,
}

def ansi_colorize(
    text: str,
    color: str = 'default',
    background: str = None,
    bold: bool = False,
    underline: bool = False
) -> str:
    """
    Wraps a string with ANSI escape codes for coloring and formatting.

    Args:
        text: The string to be colorized.
        color: The desired text color name (e.g., 'red', 'yellow').
        background: The desired background color name.
        bold: Whether to make the text bold.
        underline: Whether to make the text underlined.

    Returns:
        The formatted string with ANSI codes.
    """
    # Unicode escape character for ANSI codes
    esc = '\u001b'
    
    # List to hold all our format codes
    codes = []

    if bold:
        codes.append('1')
    if underline:
        codes.append('4')

    # Get the color code from our dictionary, defaulting to 'default' if not found
    text_color_code = TEXT_COLORS.get(color.lower(), 39)
    codes.append(str(text_color_code))
    
    # Add background color if specified
    if background:
        bg_color_code = BACKGROUND_COLORS.get(background.lower())
        if bg_color_code is not None:
            codes.append(str(bg_color_code))

    # Join all codes with a semicolon
    format_codes = ';'.join(codes)
    
    # Construct the final string with prefix and reset codes
    prefix = f'{esc}[{format_codes}m'
    reset = f'{esc}[0m'
    
    return f"{prefix}{text}{reset}"


def create_ansi_message(*messages: str) -> str:
    """
    Takes one or more strings and wraps them in a Discord 'ansi' code block.

    Args:
        *messages: A sequence of strings to include in the message body.
                   Each string will be on a new line.

    Returns:
        The final message string ready to be sent to Discord.
    """
    message_body = "\n".join(messages)
    return f"```ansi\n{message_body}\n```"