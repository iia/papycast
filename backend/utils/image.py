def do_center(image, background, display):
    if (image.height > display.HEIGHT) or (image.width > display.WIDTH):
        return None

    if (background.height != display.HEIGHT) or (background.width != display.WIDTH):
        return None

    # Centering the image on the background image.
    background.paste(
        image,
        (
            int(background.width / 2) - int(image.width / 2),
            int(background.height / 2) - int(image.height / 2)
        )
    )

    return background
