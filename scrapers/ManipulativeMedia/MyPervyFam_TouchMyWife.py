"""
Stash scraper for Blowpass (Network) that uses the Algolia API Python client
"""
import json
import re
import sys
from typing import Any

from AlgoliaAPI.AlgoliaAPI import (
    ScrapedGallery,
    ScrapedMovie,
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search
)

from py_common import log
from py_common.types import ScrapedGallery, ScrapedScene
from py_common.util import scraper_args


channel_name_map = {
    "MPF Shorts": "My Pervy Family Shorts",
}
"""
This map just contains overrides when using a channel name as the studio
"""

network_name_map = {
}
"""
Each network_name requiring a map/override should have a key-value here
"""

serie_name_map = {
}
"""
Each serie_name requiring a map/override should have a key-value here
"""

site_map = {
    "mypervyfamily": "My Pervy Family",
    "touchmywife": "Touch My Wife",
}
"""
Each site found in the logic should have a key-value here
"""

def determine_studio(api_object: dict[str, Any]) -> str | None:
    """
    Determine studio name from API object properties to use instead of the
    `studio_name` property scraped by default
    """
    available_on_site = api_object.get("availableOnSite", [])
    main_channel_name = api_object.get("mainChannel", {}).get("name")
    network_name = api_object.get("network_name")
    serie_name = api_object.get("serie_name")
    sitename = api_object.get("sitename")
    sitename_pretty = api_object.get("sitename_pretty")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"network_name: {network_name}, "
        f"serie_name: {serie_name}, "
        f"sitename: {sitename}, "
        f"sitename_pretty: {sitename_pretty}, "
    )

    # steps through api_scene["availableOnSite"], and picks the first match
    if site_match := next(
        (site for site in available_on_site if site in site_map),
        None
    ):
        log.debug(f"matched site '{site_match}'")
        return site_map.get(site_match, site_match)
    if serie_name in [
        *serie_name_map,
    ]:
        log.debug(f"matched serie_name '{serie_name}'")
        return serie_name_map.get(serie_name, serie_name)
    if main_channel_name:
        log.debug(f"matched main_channel_name '{main_channel_name}'")
        # most scenes have the studio name as the main channel name
        return channel_name_map.get(main_channel_name, main_channel_name)
    return None


def postprocess_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """
    if studio_override := determine_studio(api_scene):
        scene["studio"] = { "name": studio_override }

    return scene


def postprocess_gallery(gallery: ScrapedGallery, api_gallery: dict[str, Any]) -> ScrapedGallery:
    """
    Applies post-processing to the gallery
    """
    if studio_override := determine_studio(api_gallery):
        gallery["studio"] = { "name": studio_override }

    return gallery


def sitename_from_url(_url: str) -> str | None:
    """
    Extracts the sitename part of a URI path
    """
    if match := re.search(r"/en/video/(.*)/.*/\d+$", _url.lower()):
        if match.group(1) in domains:
            yield [match.group(1)]


if __name__ == "__main__":
    domains = [
        "mypervyfamily",
        "touchmywife",
    ]
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = gallery_from_url(url, sites, postprocess=postprocess_gallery)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites, postprocess=postprocess_gallery)
        case "scene-by-url", {"url": url, "extra": extra} if url and extra:
            sites = next(sitename_from_url(url), None)
            result = scene_from_url(url, sites, postprocess=postprocess_scene)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = domains
            result = scene_search(name, sites, postprocess=postprocess_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = next(sitename_from_url(args['url']), None)
            result = scene_from_fragment(args, sites, postprocess=postprocess_scene)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=postprocess_movie)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            print("null")
            sys.exit(1)

    print(json.dumps(result))
