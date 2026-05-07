def parse_order(text):
    text = text.lower()

    items = []

    if "milk" in text:
        items.append("milk")
    if "bread" in text:
        items.append("bread")
    if "egg" in text:
        items.append("eggs")

    return items