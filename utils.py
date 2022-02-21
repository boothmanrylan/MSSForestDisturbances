import ee

def copyproperties(func):
    '''Decorator to ensure func doesn't alter image metadata.

    The first argument to func must be an ee.Image, func must also return an
    ee.Image
    '''
    def inner(image, *args, **vargs):
        image_properties = ee.Image(image).toDictionary()
        new_image = func(image, *args, **vargs)
        return new_image.set(image_properties)
    return inner

def copygeometry(func):
    '''Decorator to ensure func doesn't change image geometry.

    The first argument to func must be an ee.Image, func must also return an
    ee.Image
    '''
    def inner(image, *args, **vargs):
        image_geometry = ee.Image(image).geometry()
        new_image = func(image, *args, **vargs)
        return new_image.clip(image_geometry)
    return inner
