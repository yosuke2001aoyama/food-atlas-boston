import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../", import.meta.url);
const readJson = async path => JSON.parse(await readFile(new URL(path, root), "utf8"));
const [restaurantsData, checksData, cuisines, html, app] = await Promise.all([
  readJson("data/restaurants.json"),
  readJson("data/checks.json"),
  readJson("data/cuisines.json"),
  readFile(new URL("index.html", root), "utf8"),
  readFile(new URL("app.js", root), "utf8"),
]);

const normalize = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
const restaurantNames = new Set(restaurantsData.restaurants.map(restaurant => normalize(restaurant.name)));
const japaneseRestaurants = restaurantsData.restaurants.filter(restaurant => restaurant.country === "Japan");
const officialImageRestaurants = restaurantsData.restaurants.filter(restaurant => /^https:\/\//.test(restaurant.image_url || ""));
const imageIds = new Set([...app.matchAll(/foodPhoto\("(photo-[^"]+)"/g)].map(match => match[1]));
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

console.log(JSON.stringify({
  status: "passed",
  restaurants: restaurantsData.count,
  japaneseRestaurants: japaneseRestaurants.length,
  cuisines: cuisines.length,
  checks: checksData.count,
  officialImageRestaurants: officialImageRestaurants.length,
  coverImages: imageIds.size,
}));
