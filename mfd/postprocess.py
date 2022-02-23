import ee
import msslib

from . import get_collection
from .utils import copyproperties

BUFFERED_QUEBEC = get_collection.QUEBEC.buffer(50000)

# every MSS image over QC during the study period
ALL_MSS = get_collection.get_collection(BUFFERED_QUEBEC, 1972, 1984, 40)

_land_cover = ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V-C3/Global")
_builtup_areas = _land_cover.first().select('urban-coverfraction').gt(0)
_cropland = _land_cover.first().select('crops-coverfraction').gt(20)
INVALID_REGIONS = _builtup_areas.Or(_cropland)


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
    im = get_matching_image(event)
    blank_pixels = im.select([0, 1, 2, 3]).reduce(ee.Reducer.sum()).lte(5)
    return event.where(blank_pixels, 0)


def apply_msscvm(event,
                 replace_all=False,
                 shadow_val=4,
                 cloud_val=5,
                 burn_val=2):
    im = get_matching_image(event)
    im = msslib.calcToa(im)
    clouds = msslib.cloudLayer(im)
    dem = msslib.getDem(im)
    shadows = msslib.shadowLayer(im, dem, clouds)
    return ee.Algorithms.If(
        replace_all,
        im.where(shadows, shadow_val).where(clouds, cloud_val),
        im.where(shadows.And(im.eq(burn_val)),
                 shadow_val).where(clouds.And(im.eq(burn_val)), cloud_val))


@copyproperties
def postprocess(event, mask_clouds=False, **args):
    event = event.where(INVALID_REGIONS.And(event.eq(2)), 1)
    if (mask_clouds):
        event = apply_msscvm(event, **args)
    return drop_all_blank_pixels(event)


@copyproperties
def squash_extra_classes(event):
    original_bands = event.bandNames()
    output = event.remap([1, 2, 3], [1, 2, 1], 0).selfMask().subtract(1)
    return output.rename(original_bands)


def _carry_observations_forward(event, previous_events):

    @copyproperties
    def _blend(top, bottom):
        return bottom.blend(top)

    return previous_events.add(_blend(event, previous_events.get(-1)))


def carry_observations_forward(events):
    first = ee.List([ee.Image(0).set("year", 1972)])
    result = events.iterate(_carry_observations_forward, first)
    # slice(1) to drop the blank image iterate starts with
    return result.toBands().slice(1)


@copyproperties
def get_burn_year(event):
    event = event.selfMask()
    year = ee.Number(event.get("year")).inti()
    return event.multiply(year).int()


def get_burn_year_spread(events):
    burn_years = events.map(get_burn_year)
    max_burn_year = burn_years.reduce(ee.Reducer.max())
    min_burn_year = burn_years.reduce(ee.Reducer.min())
    return max_burn_year.subtract(min_burn_year)


def get_year_from_index(events, index_image):
    events_list = events.toList(events.size())

    indices = ee.List.sequence(0, events.size().subtract(1))
    years = indices.map(lambda i: ee.Image(events_list.get(i)).get("year"))
    return index_image.remap(indices, years).int()


def filter_and_clip(events, geometry):
    events = events.filterBounds(geometry)
    events = events.map(lambda event: event.clip(geometry))
    return events
