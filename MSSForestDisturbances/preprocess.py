from msslib import msslib
import ee

from utils import copyproperties, copygeometry

MAX_BAI = 800


@copyproperties
def standardize_single(image, band):
    image = ee.Image(image).select([band])
    median = image.reduceRegion(
        reducer=ee.Reducer.median(),
        maxPixels=1e15,
        scale=60,
        geometry=image.geometry()
    )

    return image.subtract(median.toImage())


@copyproperties
def standardize(image):
    image = ee.Image(image)
    bands = image.bandNames()
    output = bands.iterate(
        lambda b, i: ee.Image(i).addBands(standardize_single(image, b)),
        ee.Image())
    output = ee.Image(output).select(bands)
    return output


@copyproperties
def burned_area_index(image):
    bai = image.expression(
        '1.0 / ((0.1 - RED)**2 + (0.06 - NIR)**2)',
        {'NIR': image.select('nir'), 'RED': image.select('red')}
    )
    return bai


@copyproperties
def get_MSS_tasseled_cap(image):
    coefs = ee.Array([[0.433, 0.632, 0.586, 0.264],
                      [-0.290, -0.562, 0.600, 0.491],
                      [-0.829, 0.522, -0.039, 0.194],
                      [0.223, 0.012, -0.543, 0.810]])
    array_image_1d = image.select([0, 1, 2, 3]).toArray()
    array_image_2d = array_image_1d.toArray(1)

    components_image = ee.Image(coefs).matrixMultiply(array_image_2d)
    components_image = components_image.arrayProject([0])
    components_image = components_image.arrayFlatten(
        [['Brightness', 'Greenness', 'Yellowness', 'Nonesuch']]
    )

    return components_image


@copyproperties
def get_TCA(image):
    brightness = ee.Image(image.select('Brightness'))
    greenness = ee.Image(image.select('Greenness'))
    tca = greenness.divide(brightness).atan().rename(['tca'])

    return tca


@copygeometry
@copyproperties
def preprocess(image):
    image = ee.Image(image)

    toa_image = ee.Image(msslib.calcToa(image))
    masked_toa_image = ee.Image(msslib.applyMsscvm(toa_image))
    cloud_mask = toa_image.mask()

    tasseled_cap = ee.Image(get_MSS_tasseled_cap(image.updateMask(cloud_mask)))

    water_mask = msslib.waterLayer(toa_image).eq(0)

    masked_toa_image = masked_toa_image.updateMask(water_mask)
    tasseled_cap = tasseled_cap.updateMask(water_mask)

    tca = ee.Image(get_TCA(tasseled_cap))
    bai = ee.Image(burned_area_index(toa_image)).rename('bai')
    ndvi = toa_image.normalizedDifference(['nir', 'red']).rename('ndvi')

    cloud_index = toa_image.normalizedDifference(['green', 'red'])
    cloud_index = cloud_index.rename('cloud_index')

    bai = bai.clamp(0, MAX_BAI).divide(MAX_BAI)

    output = toa_image.addBands(tca).addBands(bai).addBands(ndvi)
    output = output.addBands(cloud_index)

    output = ee.Image(standardize(output))

    return output.float()
