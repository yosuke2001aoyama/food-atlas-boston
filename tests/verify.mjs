import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const root = new URL("../", import.meta.url);
const require = createRequire(import.meta.url);
const readJson = async path => JSON.parse(await readFile(new URL(path, root), "utf8"));
const [restaurantsData, checksData, cuisines, html, app, exteriorPhotoApi, robots, sitemap, cuisineIndex] = await Promise.all([
  readJson("data/restaurants.json"),
  readJson("data/checks.json"),
  readJson("data/cuisines.json"),
  readFile(new URL("index.html", root), "utf8"),
  readFile(new URL("app.js", root), "utf8"),
  readFile(new URL("api/exterior-photo.js", root), "utf8"),
  readFile(new URL("robots.txt", root), "utf8"),
  readFile(new URL("sitemap.xml", root), "utf8"),
  readFile(new URL("cuisines/index.html", root), "utf8"),
]);

const normalize = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
const restaurantNames = new Set(restaurantsData.restaurants.map(restaurant => normalize(restaurant.name)));
const japaneseRestaurants = restaurantsData.restaurants.filter(restaurant => restaurant.country === "Japan");
const officialImageRestaurants = restaurantsData.restaurants.filter(restaurant => /^https:\/\//.test(restaurant.image_url || ""));
const imageIds = new Set([...app.matchAll(/foodPhoto\("(photo-[^"]+)"/g)].map(match => match[1]));
const representedCuisines = cuisines.filter(cuisine => restaurantsData.restaurants.some(restaurant => restaurant.country === cuisine.country));
const cuisineDirectories = (await readdir(new URL("cuisines/", root), { withFileTypes: true })).filter(entry => entry.isDirectory()).map(entry => entry.name).sort();
const cuisinePages = await Promise.all(cuisineDirectories.map(directory => readFile(new URL(`cuisines/${directory}/index.html`, root), "utf8")));
const requiredOriginalRestaurants = [
  "Izakaya Ittoku", "Yume Wo Katare", "Tsurumen Davis", "Yume Ga Arukara", "Cafe Mami",
  "Sugidama Soba & Izakaya", "Nagomi Izakaya", "Sakura Japanese", "Genki Ya", "Sapporo Ramen",
  "Tampopo", "Cafe Sushi", "O Ya", "Hokkaido Ramen Santouka Harvard Square",
];

assert.equal(cuisines.length, 52, "All 52 original cuisine categories must remain available");
assert.ok(restaurantsData.count >= 2000, `Expected at least 2,000 restaurants, received ${restaurantsData.count}`);
assert.equal(restaurantsData.count, restaurantsData.restaurants.length, "Restaurant metadata count must match payload");
assert.ok(japaneseRestaurants.length >= 96, "Japanese coverage must not regress below the original app's 96-place baseline");
assert.equal(checksData.count, 11, "All 11 published HomeTaste checks must be preserved");
assert.equal(restaurantNames.size, restaurantsData.restaurants.length, "Canonical restaurant names must be unique");
assert.ok(officialImageRestaurants.length >= 2, "Direct OSM image metadata must be preserved when usable");

for (const name of requiredOriginalRestaurants) {
  assert.ok(restaurantNames.has(normalize(name)), `Missing original restaurant: ${name}`);
}
for (const check of checksData.checks) {
  assert.ok(restaurantNames.has(normalize(check.restaurant)), `Published check has no matching restaurant: ${check.restaurant}`);
}

assert.match(html, /All 52 cuisines/, "The default filter must visibly include every cuisine");
assert.match(html, /Complete dataset/, "The data integrity state must be visible");
assert.match(html, /leaflet\.markercluster/, "The map must cluster the complete result set");
assert.match(app, /selectedCuisine:\s*"all"/, "The product must not default to Japanese only");
assert.ok(imageIds.size >= 35, "Restaurant covers must draw from a diverse image library");
for (const category of ["japanSushi", "japanRamen", "japanNoodles", "japanCurry", "japanIzakaya", "japanGrill", "japanRice", "japanCafe", "japanClassic"]) {
  assert.match(app, new RegExp(`${category}: \\[`, "m"), `Missing Japanese cover category: ${category}`);
}
assert.match(app, /imageCategoryFor\(restaurant\)/, "Covers must be selected from restaurant-level cuisine data");
assert.match(app, /restaurant\.image_url/, "Direct restaurant image metadata must take priority when present");
assert.doesNotMatch(app, /imageFor\(restaurant\.country\)/, "Country-wide cover reuse must not return");
assert.match(app, /\/api\/exterior-photo\?lat=/, "Visible restaurant covers must request nearby street-level imagery");
assert.match(app, /IntersectionObserver/, "Exterior lookup must stay lazy and limited to visible cards");
assert.match(app, /KartaView · CC BY-SA 4\.0/, "Every street-level image must visibly retain its source and license");
assert.match(app, /data-fallback/, "Missing or broken exterior photos must preserve the existing cuisine cover");
assert.match(exteriorPhotoApi, /MAX_DISTANCE_METERS = 42/, "Exterior candidates must stay close to the restaurant coordinates");
assert.match(exteriorPhotoApi, /MAX_DIRECTION_DIFFERENCE = 58/, "Exterior candidates must face toward the restaurant");
assert.match(exteriorPhotoApi, /projection === "SPHERE"/, "Uncropped panoramic imagery must not be used as a cover");
assert.match(exteriorPhotoApi, /cdn\.kartaview\.org/, "Exterior image URLs must be restricted to trusted KartaView hosts");
assert.match(exteriorPhotoApi, /latitude < 41\.8/, "Exterior lookup coordinates must be restricted to the Boston area");
const { chooseExteriorPhoto } = require(fileURLToPath(new URL("api/exterior-photo.js", root)));
const restaurantCoordinates = [42.36, -71.058];
const facingCandidate = {
  id: "101",
  sequenceId: "202",
  sequenceIndex: "3",
  lat: 42.3598,
  lng: -71.058,
  heading: 0,
  fieldOfView: 70,
  projection: "PLANE",
  visibility: "public",
  status: "active",
  imageProcUrl: "https://cdn.kartaview.org/example.jpg",
};
assert.equal(chooseExteriorPhoto([facingCandidate], ...restaurantCoordinates)?.photo.id, "101", "A close photo facing the restaurant should be accepted");
assert.equal(chooseExteriorPhoto([{ ...facingCandidate, heading: 180 }], ...restaurantCoordinates), null, "A photo facing away from the restaurant should be rejected");
assert.equal(chooseExteriorPhoto([{ ...facingCandidate, projection: "SPHERE" }], ...restaurantCoordinates), null, "An uncropped panorama should be rejected");
assert.equal(chooseExteriorPhoto([{ ...facingCandidate, imageProcUrl: "https://example.com/not-trusted.jpg" }], ...restaurantCoordinates), null, "An untrusted image host should be rejected");

assert.match(html, /<link rel="canonical" href="https:\/\/hometaste-boston\.vercel\.app\/"/, "Homepage must declare its production canonical URL");
assert.match(html, /<meta name="robots" content="index,follow/, "Homepage must explicitly allow indexing");
assert.match(html, /"@type": "WebSite"/, "Homepage must provide WebSite structured data");
assert.match(html, /property="og:title"/, "Homepage must provide social/search sharing metadata");
assert.match(html, /href="\/cuisines"/, "Homepage must link to the crawlable cuisine directory");
assert.match(app, /<a class="cuisine-card/, "Featured cuisines must render as crawlable anchor links");
assert.match(app, /new URLSearchParams\(window\.location\.search\)\.get\("cuisine"\)/, "Cuisine map links must restore their selected filter");

assert.match(robots, /^User-agent: \*$/m, "robots.txt must address all crawlers");
assert.match(robots, /^Allow: \/$/m, "robots.txt must allow the site");
assert.match(robots, /Sitemap: https:\/\/hometaste-boston\.vercel\.app\/sitemap\.xml/, "robots.txt must advertise the production sitemap");
const sitemapLocations = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(match => match[1]);
assert.equal(sitemapLocations.length, representedCuisines.length + 2, "Sitemap must include home, cuisine index, and every represented cuisine");
assert.equal(new Set(sitemapLocations).size, sitemapLocations.length, "Sitemap URLs must be unique");
assert.ok(sitemapLocations.every(url => url.startsWith("https://hometaste-boston.vercel.app/")), "Sitemap must use absolute production URLs");

assert.equal(cuisineDirectories.length, representedCuisines.length, "Every represented cuisine must have one static landing page");
assert.match(cuisineIndex, /Boston restaurants,<br \/>organized by cuisine/, "Cuisine index must contain useful visible browse content");
const pageTitles = cuisinePages.map(page => page.match(/<title>([^<]+)<\/title>/)?.[1]);
const pageDescriptions = cuisinePages.map(page => page.match(/<meta name="description" content="([^"]+)"/u)?.[1]);
const pageCanonicals = cuisinePages.map(page => page.match(/<link rel="canonical" href="([^"]+)"/u)?.[1]);
assert.equal(new Set(pageTitles).size, cuisinePages.length, "Cuisine page titles must be unique");
assert.equal(new Set(pageDescriptions).size, cuisinePages.length, "Cuisine page descriptions must be unique");
assert.equal(new Set(pageCanonicals).size, cuisinePages.length, "Cuisine page canonical URLs must be unique");
for (const page of cuisinePages) {
  assert.match(page, /"@type":"CollectionPage"/, "Cuisine page must expose CollectionPage structured data");
  assert.match(page, /"@type":"BreadcrumbList"/, "Cuisine page must expose breadcrumb structured data");
  assert.match(page, /"@type":"ItemList"/, "Cuisine page must expose its restaurant list as structured data");
  assert.match(page, /href="\/\?cuisine=[^"]+#explore"/, "Cuisine page must link back to the filtered live map");
}

console.log(JSON.stringify({
  status: "passed",
  restaurants: restaurantsData.count,
  japaneseRestaurants: japaneseRestaurants.length,
  cuisines: cuisines.length,
  checks: checksData.count,
  officialImageRestaurants: officialImageRestaurants.length,
  coverImages: imageIds.size,
  seoCuisinePages: cuisinePages.length,
  sitemapUrls: sitemapLocations.length,
}));
