import os
import ee

def export_collection(image_collection, id_property, output_asset,
                      skip=None, max_tasks=None, check=True):
    input_collection = ee.ImageCollection(image_collection)
    input_ids = image_collection.aggregate_array(id_property).getInfo()

    try:  # create the output asset if it does not exist
        test = ee.ImageCollection(output_asset).first().getInfo()
    except ee.EEException as e:
        raise ValueError(f'{output_asset} does not exist!') from e

    if skip is not None:
        input_ids = input_ids[skip:]

    if max_tasks is not None:
        input_ids = input_ids[:max_tasks]

    if check: # dont export images that have already been exported
        output_collection = ee.ImageCollection(output_asset)
        output_ids = output_collection.aggregate_array(id_property)
        input_ids = [x for x in input_ids if x not in output_ids]

    for id in input_ids:
        im = image_collection.filter(ee.Filter.eq(id_property, id)).first()
        task = ee.batch.Export.image.toAsset(
            image=im, description=id,
            assetId=os.path.join(output_asset, id),
            pyramidingPolicy={'.default': 'mode'}, region=im.geometry(),
            scale=60, maxPixels=1e10
        )
        task.start()
