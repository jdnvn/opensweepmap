def schedule_to_color(schedule_id: int) -> str:
    if schedule_id is None:
        return "#000000"
    # Normalize hash to the range 0-1
    normalized = schedule_id / 3884.0

    # Convert to RGB color
    r = int(normalized * 256)
    g = int((normalized * 256 * 256) % 256)
    b = int((normalized * 256 * 256 * 256) % 256)

    # Convert to hex color
    color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
    return color