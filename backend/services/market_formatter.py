"""Market Name Formatter Utility for OkaMoney AI Tips

Ensures all market names and selections are clear, unambiguous, and user-friendly.
No abbreviations like "O0.5 1H" - always use full names like "Over 0.5 First Half Goals"
"""

# Standard market name mappings - converts any abbreviated form to full clear form
MARKET_NAME_MAPPINGS = {
    # Goals Markets
    'O0.5 1H Goals': 'Over 0.5 First Half Goals',
    'O0.5 1H': 'Over 0.5 First Half Goals',
    'Over 0.5 1H Goals': 'Over 0.5 First Half Goals',
    'Over 0.5 1H': 'Over 0.5 First Half Goals',
    
    'O0.5 2H Goals': 'Over 0.5 Second Half Goals',
    'O0.5 2H': 'Over 0.5 Second Half Goals',
    'Over 0.5 2H Goals': 'Over 0.5 Second Half Goals',
    'Over 0.5 2H': 'Over 0.5 Second Half Goals',
    
    'Under 1.5 1H': 'Under 1.5 First Half Goals',
    'U1.5 1H': 'Under 1.5 First Half Goals',
    'U1.5 1H Goals': 'Under 1.5 First Half Goals',
    
    'Over 1.5': 'Over 1.5 Total Goals',
    'O1.5': 'Over 1.5 Total Goals',
    'O1.5 Goals': 'Over 1.5 Total Goals',
    
    'Over 2.5': 'Over 2.5 Total Goals',
    'O2.5': 'Over 2.5 Total Goals',
    'O2.5 Goals': 'Over 2.5 Total Goals',
    'Over 2.5 Goals': 'Over 2.5 Total Goals',
    
    'Under 3.5': 'Under 3.5 Total Goals',
    'U3.5': 'Under 3.5 Total Goals',
    'U3.5 Goals': 'Under 3.5 Total Goals',
    
    'Under 4.5': 'Under 4.5 Total Goals',
    'U4.5': 'Under 4.5 Total Goals',
    'U4.5 Goals': 'Under 4.5 Total Goals',
    
    # Corners Markets
    'O4.5 1H Corners': 'Over 4.5 First Half Corners',
    'Over 4.5 1H Corners': 'Over 4.5 First Half Corners',
    
    'O8.5 Corners': 'Over 8.5 Total Corners',
    'Over 8.5 Corners': 'Over 8.5 Total Corners',
    
    'O9.5 Corners': 'Over 9.5 Total Corners',
    'Over 9.5 Corners': 'Over 9.5 Total Corners',
    
    'U10.5 Corners': 'Under 10.5 Total Corners',
    'Under 10.5 Corners': 'Under 10.5 Total Corners',
    
    # Cards Markets
    'O2.5 Cards': 'Over 2.5 Total Cards',
    'Over 2.5 Cards': 'Over 2.5 Total Cards',
    
    'O3.5 Cards': 'Over 3.5 Total Cards',
    'Over 3.5 Cards': 'Over 3.5 Total Cards',
    
    'U4.5 Cards': 'Under 4.5 Total Cards',
    'Under 4.5 Cards': 'Under 4.5 Total Cards',
    
    # BTTS
    'BTTS': 'Both Teams To Score - Yes',
    'BTTS Yes': 'Both Teams To Score - Yes',
    'BTTS - Yes': 'Both Teams To Score - Yes',
    
    # Team Goals
    'Team O0.5 2H': 'Team Over 0.5 Second Half Goals',
    'Home Team Over 0.5 2H Goals': 'Home Team Over 0.5 Second Half Goals',
    'Away Team Over 0.5 2H Goals': 'Away Team Over 0.5 Second Half Goals',
}


def format_selection(selection: str) -> str:
    """
    Format a market selection to be clear and unambiguous.
    Converts any abbreviated form to the full clear form.
    
    Examples:
        "O0.5 1H Goals" → "Over 0.5 First Half Goals"
        "Under 1.5 1H" → "Under 1.5 First Half Goals"
        "BTTS" → "Both Teams To Score - Yes"
    """
    if not selection:
        return selection
    
    # Check direct mapping
    if selection in MARKET_NAME_MAPPINGS:
        return MARKET_NAME_MAPPINGS[selection]
    
    # Handle team-specific goals (e.g., "Liverpool Over 0.5 2H Goals")
    for abbrev, full in MARKET_NAME_MAPPINGS.items():
        if abbrev in selection:
            return selection.replace(abbrev, full)
    
    return selection


def format_market_name(market: str) -> str:
    """
    Format a market name to be clear and descriptive.
    """
    if not market:
        return market
    
    # Check direct mapping
    if market in MARKET_NAME_MAPPINGS:
        return MARKET_NAME_MAPPINGS[market]
    
    return market


def format_pick(pick: dict) -> dict:
    """
    Format a pick/prediction dictionary to have clear market names.
    """
    if not pick:
        return pick
    
    formatted = pick.copy()
    
    if 'selection' in formatted:
        formatted['selection'] = format_selection(formatted['selection'])
    
    if 'market' in formatted:
        formatted['market'] = format_market_name(formatted['market'])
    
    return formatted


def format_ticket(ticket: dict) -> dict:
    """
    Format an entire ticket (with legs) to have clear market names.
    """
    if not ticket:
        return ticket
    
    formatted = ticket.copy()
    
    if 'legs' in formatted:
        formatted['legs'] = [format_pick(leg) for leg in formatted['legs']]
    
    if 'markets' in formatted:
        formatted['markets'] = [format_pick(market) for market in formatted['markets']]
    
    return formatted


def format_game(game: dict) -> dict:
    """
    Format a game with its markets to have clear market names.
    """
    if not game:
        return game
    
    formatted = game.copy()
    
    if 'markets' in formatted:
        formatted['markets'] = [format_pick(market) for market in formatted['markets']]
    
    return formatted
