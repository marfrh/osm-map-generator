# dict of map targets
map_targets = {}

# Contourline settings. Only the parameters listed here are supported,
# see pyhgtap documentation for available values
# 1" contourline settings
contour1 = {
    "contourline_source": "view1",
    "stepsize": "10",
    "major_medium": "500,50",
    "epsilon": "0.00001",
}

# 3" contourline settings
contour3 = {
    "contourline_source": "view3",
    "stepsize": "20",
    "major_medium": "500,10",
    "epsilon": "0.0001",
}

# use custom hgt files
contour1_custom = {
    "contourline_source": "custom",
    "custom_hgt_dir": "tmp/hgt/custom/",
    "stepsize": "10",
    "major_medium": "500,50",
    "epsilon": "0.00001",
}

# map target template with default settings
default_map_dict = {
    "name": "",
    "source": "",
    "has_sea": False,
    "use_land_grid_split": False,
    "has_crags": False,
    "use_polygon_shape": False,
    "preferred_languages": "de,en",
    "tag-mapping": "tt_tm/tagmapping-min.xml",
    "simplification-factor": 2.5,
    "zoom-interval-conf": "5,0,7,10,8,11,14,12,21",
}

# Loro_Ciuffenna
# Test map including hiking/mtb routes and osmc symbols
t = default_map_dict.copy()
src = "http://download.geofabrik.de/europe/italy/centro-latest.osm.pbf"
t["name"] = "Loro_Ciuffenna"
t["source"] = src
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1_custom
map_targets[t["name"]] = t

# Canary_Islands
# Test map, only works with custom 1" hgt files, see README
t = default_map_dict.copy()
src = "http://download.geofabrik.de/africa/canary-islands-latest.osm.pbf"
t["name"] = "Canary_Islands"
t["source"] = src
t["has_sea"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en,es"
t["contour"] = contour1_custom
map_targets[t["name"]] = t

# Montenegro
t = default_map_dict.copy()
src = "http://download.geofabrik.de/europe/montenegro-latest.osm.pbf"
t["name"] = "Montenegro"
t["source"] = src
t["has_sea"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en,sh,sl,sr,hy,hr,mk"
t["contour"] = contour3
map_targets[t["name"]] = t

# Italy_Centro
t = default_map_dict.copy()
src = "http://download.geofabrik.de/europe/italy/centro-latest.osm.pbf"
t["name"] = "Italy_Centro"
t["source"] = src
t["has_sea"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1
map_targets[t["name"]] = t

# Wallmersdorf
# Test map including building-relations with housenumbers
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/austria-latest.osm.pbf"
t["name"] = "Wallmersdorf"
t["source"] = src
t["tag-mapping"] = "tt_tm/tagmapping-urban.xml"
t["contour"] = contour1
map_targets[t["name"]] = t

# Great_Britain
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/great-britain-latest.osm.pbf"
t["name"] = "Great_Britain"
t["source"] = src
t["has_sea"] = True
t["has_crags"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en"
t["tag-mapping"] = "tt_tm/tagmapping-urban.xml"
t["contour"] = contour1
map_targets[t["name"]] = t

# Uruguay
# Test map for admin relations
t = default_map_dict.copy()
src = "http://download.geofabrik.de/south-america/uruguay-latest.osm.pbf"
t["name"] = "Uruguay"
t["source"] = src
t["has_sea"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "en,es,de"
t["contour"] = contour3
map_targets[t["name"]] = t

# Alps
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe-latest.osm.pbf"
t["name"] = "Alps"
t["source"] = src
t["has_sea"] = True
t["use_land_grid_split"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en,fr,it,sl"
t["tag-mapping"] = "tt_tm/tagmapping-min.xml"
t["contour"] = contour1_custom
t["zoom-interval-conf"] = "5,0,5,6,6,7,10,8,11,14,12,21"
map_targets[t["name"]] = t

# Italy
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe-latest.osm.pbf"
t["name"] = "Italy"
t["source"] = src
t["has_sea"] = True
t["use_land_grid_split"] = True
t["use_polygon_shape"] = True
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1_custom
map_targets[t["name"]] = t

# Kaltern
# Test map with mtb route and cycle route sharing the same way (40926951)
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf"
t["name"] = "Kaltern"
t["source"] = src
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1
map_targets[t["name"]] = t

# Alleghe
# Test map with piste routes
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/italy/nord-est-latest.osm.pbf"
t["name"] = "Alleghe"
t["source"] = src
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1
map_targets[t["name"]] = t

# Bruegge
# Test map with cylce-highways
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/belgium-latest.osm.pbf"
t["name"] = "Bruegge"
t["source"] = src
t["has_sea"] = True
t["preferred_languages"] = "de,en,nl,fr"
t["tag-mapping"] = "tt_tm/tagmapping-urban.xml"
t["contour"] = contour1
map_targets[t["name"]] = t

# Breuil_Cervinia
# Test map with piste multipolygon-relation on the below the large lake on the
# right side
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/italy/nord-ovest-latest.osm.pbf"
t["name"] = "Breuil_Cervinia"
t["source"] = src
t["preferred_languages"] = "de,en,it"
t["contour"] = contour1
map_targets[t["name"]] = t

# Wales
# Test map with os-open-data crags
t = default_map_dict.copy()
src = "https://download.geofabrik.de/europe/great-britain/wales-latest.osm.pbf"
t["name"] = "Wales"
t["source"] = src
t["has_sea"] = True
t["has_crags"] = True
t["preferred_languages"] = "en,de,cy"
t["contour"] = contour1
map_targets[t["name"]] = t
