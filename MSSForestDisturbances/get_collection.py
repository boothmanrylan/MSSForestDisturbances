import ee
from itertools import chain
from msslib import msslib

from .bad_image_ids import ALL_BAD_IDS

QUEBEC = ee.Geometry.Polygon([[[-79.78241843158267, 62.61567948606001],
                               [-79.78241843158267, 44.98359841279507],
                               [-56.99128073627017, 44.98359841279507],
                               [-56.99128073627017, 62.61567948606001]]],
                             None, False)


def get_collection(aoi, start_year, end_year=None, max_cloud_cover=25):
    end_year = start_year if end_year is None else end_year

    bad_ids = [ALL_BAD_IDS[x] for x in range(start_year, end_year + 1)]
    bad_ids = list(chain.from_iterable(bad_ids))

    collection = msslib.getCol(
        aoi=aoi,
        doyRange=[120, 270],  # ~May 1st to Sept 30th
        yearRange=[start_year, end_year],
        maxCloudCover=max_cloud_cover,
        maxRmseVerify=0.5,
        excludeIds=bad_ids
    )

    return collection
