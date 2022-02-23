from functools import wraps

import ee

CLASS_VIS = {
    'min': 0,
    'max': 5,
    'palette': ['grey', 'saddleBrown', 'red', 'blue', 'black', 'white']
}

RAINBOW_PALETTE = {
    'A0A0A0', 'FF0000', 'FF1700', 'FF2F00', 'FF4700', 'FF5E00',
    'FF7600', 'FF8E00', 'FFA600', 'FFBD00', 'FFD500', 'FFED00',
    'F9FF00', 'E1FF00', 'C9FF00', 'B1FF00', '9AFF00', '82FF00',
    '6AFF00', '53FF00', '3BFF00', '23FF00', '0BFF00', '00FF0B',
    '00FF23', '00FF3B', '00FF53', '00FF6A', '00FF82', '00FF9A',
    '00FFB1', '00FFC9', '00FFE1', '00FFF9', '00EDFF', '00D5FF',
    '00BDFF', '00A6FF', '008EFF', '0076FF', '005EFF', '0047FF',
    '002FFF', '0017FF', '0000FF',
}


def copyproperties(func):
    """Decorator to ensure func doesn't alter image metadata.

    The first argument to func must be an ee.Image, func must also return an
    ee.Image
    """

    @wraps(func)
    def inner(image, *args, **vargs):
        image_properties = ee.Image(image).toDictionary()
        time = image.get("system:time_start")
        new_image = func(image, *args, **vargs)
        return new_image.set(image_properties).set("system:time_start", time)

    return inner


def copygeometry(func):
    """Decorator to ensure func doesn't change image geometry.

    The first argument to func must be an ee.Image, func must also return an
    ee.Image
    """

    @wraps(func)
    def inner(image, *args, **vargs):
        image_geometry = ee.Image(image).geometry()
        new_image = func(image, *args, **vargs)
        return new_image.clip(image_geometry)

    return inner
