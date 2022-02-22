import ee
import msslib

import get_collection
from utils import copyproperties, copygeometry

BUFFERED_QUEBEC = get_collection.quebec.buffer(50000)

# every MSS image over QC during the study period
ALL_MSS = get_collection.get_collection(BUFFERED_QUEBEC, 1972, 1984, 40)

_land_cover = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/GLobal")
_builtup_areas = _land_cover.first().select('urban-coverfraction').gt(0)
_cropland = _land_cover.first().select('crops-coverfraction').gt(20)
INVALID_REGIONS = _builtup_areas.or(_cropland)

_sea_surface = ee.ImageCollection("HYCOM/sea_surface_elevation")
_sea_surface = _sea_surface.filterDate('2021-01-01', '2021-12-31').first()
_sea_surface = _sea_surface.unmask().eq(0).clip(BUFFERED_QUEBEC)
_kernel = ee.Kernel.circle(radius=100)
OCEAN_MASK = _sea_surface.focalMax(kernel=_kernel, iterations=4)

def set_true_date(im):
    date = im.get('DATE_ACQUIRED')
    millis = ee.Date.parse('YYYY-MM-dd', date).millis()
    return im.set('system:time_start', millis)

def get_mask(event):
    return event.remap([0, 1, 2, 3, 4, 5], [0, 1, 1, 1, 0, 0])

def get_matching_image(event, apply_mask=False):
    scene_id = event.get("LANDSAT_SCENE_ID")
    image = ALL_MSS.filter(ee.Filter.eq("LANDSAT_SCENE_ID", scene_id)).first()
    if apply_mask:
        mask = get_mask(event)
        image = image.updateMask(mask)
    return image

@copyproperties
def drop_all_blank_pixels(event):
    im = get_matching_iamge(event)
    blank_pixels = im.select([0, 1, 2, 3]).reduce(ee.Reducer.sum()).lte(5)
    return event.where(blank_pixels, 0)

def apply_msscvm(event, replace_all=False, shadow_val=4, cloud_val=5,
                 burn_val=2):
    im = get_matching_image(event)
    im = msslib.calcToa(im)
    clouds = msslib.cloudLayer(im)
    dem = msslib.getDem(im)
    shadows = msslib.shadowLayer(im, dem, clouds)
    return ee.Algorithms.If(
        replace_all,
        im.where(shadows, shadow_val).where(clouds, cloud_val),
        im.where(
            shadows.and(im.eq(burn_val)), shadow_val
        ).where(
            clouds.and(im.eq(burn_val)), cloud_val
        )
    )

@copyproperties
def postprocess(event, mask_clouds=False, **args):
    event = event.where(INVALID_REGIONS.and(im.eq(2)), 1)
    if (mask_clouds):
        event = apply_msscvm(event, **args)
    event = drop_all_blank_pixels(event)
    return event.updateMask(OCEAN_MASK)

@copyproperties
def squash_extra_classes(event):
    original_bands = event.bandNames()
    output = event.remap([1, 2, 3], [1, 2, 1], 0).selfMask().subtract(1)
    return output.rename(original_bands)


