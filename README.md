# osm-map-generator
Python script to create mapsforge vector maps compatible to [OpenAndroMaps](https://www.openandromaps.org), based on Openstreetmap and other data sources.

## Disclaimer
- This tool has no affiliation with the OpenAndroMaps project and is not meant to compete with the project in any way. It is intended as a playground and knowledge documentation.
- Due to the complex nature of the data/topic and the used tools, I'm not able to provide support. If map targets fail or if any of the tools crash, please refer the individual projects and documentations (see [Dependencies](https://github.com/marfrh/osm-map-generator#dependencies)).

## Contents
- [Hardware Requirements](https://github.com/marfrh/osm-map-generator#hardware-requirements)
- [Dependencies](https://github.com/marfrh/osm-map-generator#dependencies)
- [Installation](https://github.com/marfrh/osm-map-generator#installation)
- [Usage](https://github.com/marfrh/osm-map-generator#usage)
- [Advanced Usage](https://github.com/marfrh/osm-map-generator#usage)
- [Implementation Details](https://github.com/marfrh/osm-map-generator#implementation-details)

## Hardware Requirements
Tested with 32GB RAM.

> [!WARNING]
> Lower RAM might fail for large maps and/or require code adjustments (e.g. the pbf file size limit after with the mapsforge-map-writer parameter `type=hd` is added).

## Dependencies
- [osmosis](https://wiki.openstreetmap.org/wiki/Osmosis)
  - Plugin [mapsforge-map-writer](https://github.com/mapsforge/mapsforge/blob/master/docs/Getting-Started-Map-Writer.md)
  - Increase Java heap space and optionally specify a folder for tmp files. <br>Example for 32GB RAM: `JAVACMD_OPTIONS="-Xms3G -Xmx26G -Djava.io.tmpdir=/path/to/tmp/dir"`
- [osmconvert](https://wiki.openstreetmap.org/wiki/Osmconvert)
- [osmfilter](https://wiki.openstreetmap.org/wiki/Osmfilter)
- [python3-GDAL](https://trac.osgeo.org/gdal/wiki/DownloadingGdalBinaries)
- [wget](https://www.gnu.org/software/wget/)
- [pyhgtmap](https://github.com/agrenott/pyhgtmap) ([PyPI](https://pypi.org/project/pyhgtmap/))
- [osmium](https://docs.osmcode.org/pyosmium/latest/) ([PyPI](https://pypi.org/project/osmium/))

In the current state, osm-map-generator will only work in a Linux environment as it relies on `wget` and lazily redirects some output to `/dev/null`. Besides, some of the required tools can have limitations under Windows.

> [!NOTE]
> OpenSUSE has pre-built packages available for `wget`, `osmosis`, `osmconvert`, `osmfilter` and `python3-GDAL` via [https://software.opensuse.org/](https://software.opensuse.org/).
> `pyhgtmap` and `osmium` can be installed via `pip`.

## Installation
1. Install and prepare [Dependencies](https://github.com/marfrh/osm-map-generator#dependencies).
2. `git clone https://github.com/marfrh/osm-map-generator.git` or download & extract zip file.

## Usage
1. Define a map target in `modules/map_targets.py` or use one of the examples.
   <br> See `default_map_dict` and `contour1` / `contour3` for available settings.
   <br>Attention: The example `Canary_Islands` only works with [custom hgt files](https://github.com/marfrh/osm-map-generator#use-of-custom-hgt-files).
3. Make sure a polygon file (`.poly`) with the same name as the map target is placed in folder `polygons/`.
   <br>[Polygon Files](https://wiki.openstreetmap.org/wiki/Osmosis/Polygon_Filter_File_Format) can be created with JOSM.
5. Run `./osm-map-generator map_name result.map`.
   <br>Option `-p` exists to use the osm planet file as source, option `-k` keeps intermediate results and the final map data osm file.
   <br>See `./osm-map-generator --help` for usage details.

> [!NOTE]
> For a quick test, try map target `Alleghe`. Running `./osm-map-generator Alleghe Alleghe.map` on a Ryzen Pro 7 8650U Laptop (32GB RAM, 50 Mbit fiber connection, limit to 6 threads) takes ~3-4 minutes.
> 
> For a full test, try `Wales` as it includes all possible data sources. Running `./osm-map-generator Wales Wales.map` on a Ryzen 7 Pro 8650U Laptop (32GB RAM, 50 Mbit fiber connection, limit to 6 threads) takes ~30 minutes. ~27 min for data downloads / extraction / conversions, ~3 min for tag-mapping and map-writer.


## Advanced Usage
### Relation blacklist
Large relations can lead to long rendering times with `mapsforge-map-writer`. To delete large or unwanted relations that otherwise are not catched by `reduce_data.py`, just add their osm id to `blacklist` in `modules/reduce_data.py`.

You can use `utilities/identify_large_relations.py` to search for blacklist candidates:
1. Run `osm-map-generator` with option `-k` to keep the final data file, e.g. `tmp/map_name_data_map.pbf`
2. Run `utilities/identify_large_relations.py -n 60000 -w 2000 tmp/map_name_data_map.pbf` to get a list of large relations with more than 60000 nodes or more than 2000 ways.

### Relation whitelist
The `whitelist` in `modules/reduce_data.py` prevents these relations from being deleted by `reduce_data.py`. Usually, all osm land/sea multipolygons (`place` = `island`, `islet`, `archipelago`, `sea`, `ocean`, `peninsula`) can be deleted before rendering, as land polygons shapes are included separately. But as always there can be exceptions, e.g. this relation ([3474227](https://www.openstreetmap.org/relation/3474227)) which does not match the coastline ([832607970](https://www.openstreetmap.org/way/832607970)). 

### Land polygon grid split
The map target option `"use_land_grid_split": True` activates a self-invented algorithm to cut large land polygons into smaller overlapping polygons. This can save a small amount of rendering time for large maps (e.g. for map target Italy grid split processing time is ~5 minutes with a benefit in `mapsforge-map-writer` rendering time of ~15 minutes).

### Use of custom hgt files
[https://sonny.4lima.de/](https://sonny.4lima.de/) provides detailed 1" and 3" hgt files for Europe. The following steps describe how to integrate these 1" hgt files in the map creation process:
1. Download the desired hgt files from [https://sonny.4lima.de/](https://sonny.4lima.de/)
2. Extract and copy the hgt files to directory `tmp/hgt/VIEW1`.
3. All filenames, which are not already listed in the index file `tmp/hgt/viewfinderHgtIndex_1.txt`, need to be added as a new entry, e.g.:
```
[http://viewfinderpanoramas.org/dem1/Extra.zip]
N27W016
N27W017
...
```
See folder `utilities` for an example entry that covers all of Europe as of mid 2023.
> [!NOTE]
> The map target example `Canary_Islands` only works with these custom hgt files and steps described above, as the area is not covered by Viewfinder Panoramas 1" data. 

## Implementation Details

### Speed
The following measures were applied to achieve a fast map creation process:
- As few merge steps as possible.
- Prefer osmconvert and osmfilter over osmosis if possible (both are way faster).
- Priority for the fastest file format: 1. pbf, 2. o5m, 3. osm.
- Data reduction routine `reduce_data.py` before final merge eliminates as many relations and ways as possible (and especially large relation types).
  - In addition to some predefined key/value combinations, every way/relation without relevant keys is being deleted.
  - Relevant keys are taken from map theme / tag-mapping.xml.
  - This step leads to a huge improvement in `mapsforge-map-writer` rendering time (Example for whole Italy: `reduce_data.py` processing time <5 minutes, rendering time without data reduction ~14h, with data reduction <5h, -66%).
- Optional [Land polygon grid split](https://github.com/marfrh/osm-map-generator#land-polygon-grid-split) that can save a small amount of rendering time.

### OSM ID ranges
Each object which is not part of the osm source data (e.g. newly created poly labels, contour lines, ...) needs an `osm id`. Negative ids are easy to handle as the don't collide with real osm ids. `osm-map-generator` uses the following id ranges / offsets:
Object category | Start osm id | Increment 
---|---|---
Map border | nodes -1 <br> ways = -1 | -1
Land polygons | nodes -10000000000 <br> ways -10000000000 | +1
Land polygons (grid split)  | nodes -20000000000 <br> ways -20000000000 | +1
Sea area | nodes -30000000000 <br> ways -30000000000 | +1
Administrative boundaries | ways -40000000000 | +1
Pistes | ways -50000000000 | +1
Routes | ways -60000000000 | +1
Resolved superroutes | relations -70000000000 | +1
Crags (OS Open Data) | nodes -80000000000 <br> ways -80000000000 <br> relations -80000000000 | +1
Contour lines | nodes 50000000000 <br> ways 50000000000 | +1
Polygon labels | nodes by offset +100000000000 | +1
Building relation housenumbers | nodes by offset +200000000000 |+1

> [!WARNING]
> `osmfilter` does not work with negative osm ids. Any filtering needs to be done before merging objects with negative ids.


### ESRI Shapefile to OSM converter
For two reasons, this project includes my own simplified ESRI shp to osm/pbf-format converter `modules/esri_shp_to_osm.py` (based on `osgeo` and `osmium`):
- In at least one case, mapsforge [shape2osm.py](https://github.com/mapsforge/mapsforge-creator/blob/master/shape2osm.py) caused a missing land area because it skipped part of a land polygon relation.
- To automate the processing of crags from OS Open Data, I needed a shp-to-osm converter that correctly handles relations with inner and outer rings and that can apply a specific osm tag set.

As a bonus, `esri_shp_to_osm.py` can create the faster `.pbf` file format.


### Features and differences to OpenAndroMaps
Please have a look at `osm-map-generator.py` or [OpenAndroMaps](https://www.openandromaps.org) for which map features to expect. The following list only describes known differences to OpenAndroMaps:
- (-) No POI generation.
- (-) No usage of mapsforge-map-writer `map-start-position`.
- (-) Though `zoom-interval-conf` and `simplification-factor` can be set for each map target, you need to figure out the optimal values by yourself. OpenAndroMaps are already optimized with these settings.
- (-) Tag-mapping is not computed "on the fly", only a predefined `tag-mapping.xml` can be used.
- (o) No text on the map border (intentionally, commented out/explained in the code).
- (o) Generated route `ref`-tags always consist of up to 7 characters.
- (+) Contour lines are generated by [pyhgtmap](https://github.com/agrenott/pyhgtmap) which is faster, instead of [phyghtmap](https://github.com/has2k1/plotnine/issues/619) in combination with osmosis-simplifyways.
- (+) For piste multipolygons, ways with role "inner" are rendered correctly (excluded from piste).
- (+) More generous OSMC symbol validation, resulting in more symbols on the map.
