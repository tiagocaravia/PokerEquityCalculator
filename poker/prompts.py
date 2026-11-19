from .card import Card, parse_card

NONE_WORDS = {"none", "-", "no", "preflop"}


def ask(prompt, default=None, parse=str, check=None): # Ask until valid; enter keeps the default
    shown = "none" if default == "" else default
    suffix = f" [{shown}]" if default is not None else ""
    while True:
        text = input(f"{prompt}{suffix}: ").strip()
        if not text:
            if default is not None:
                return default
            print("  Please enter a value.")
            continue
        try:
            value = parse(text)
        except ValueError:
            print("  That doesn't look right, try again.")
            continue
        problem = check(value) if check else None
        if problem:
            print(f"  {problem}")
            continue
        return value


def cards_from(text): # "AS KH" -> cards; "none" -> []
    if text.strip().lower() in NONE_WORDS:
        return []
    cards = [parse_card(c) for c in text.split()]
    if any(c.suit is None or c.rank not in Card.RANKS for c in cards):
        raise ValueError
    return cards


def ask_cards(prompt, default, counts, taken=()): # Cards as text, checked for count and duplicates
    def check(text):
        cards = cards_from(text)
        if len(cards) not in counts:
            return f"Need {' or '.join(map(str, counts))} cards."
        keys = [(c.rank, c.suit) for c in cards] + [(c.rank, c.suit) for c in taken]
        if len(set(keys)) != len(keys):
            return "Duplicate card."
        return None

    text = ask(prompt, default, parse=lambda t: (cards_from(t), t)[1], check=check)
    return "" if text.strip().lower() in NONE_WORDS else text.upper()


def yes(prompt, default=True): # y/n question
    answer = ask(prompt, "y" if default else "n").lower()
    return answer.startswith("y")


def again():
    print()
    return yes("Try another? (y/n)", default=False)


def interactive_loop(fn): # Ctrl-C / Ctrl-D quits quietly
    try:
        fn()
    except (EOFError, KeyboardInterrupt):
        print()
