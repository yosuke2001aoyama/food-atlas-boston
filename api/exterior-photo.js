const KARTAVIEW_PHOTO_API = "https://api.openstreetcam.org/2.0/photo/";
const MAX_DISTANCE_METERS = 42;
const MAX_DIRECTION_DIFFERENCE = 58;

function numeric(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function distanceMeters(fromLat, fromLng, toLat, toLng) {
  const radians = value => value * Math.PI / 180;
  const earthRadius = 6371000;
  const latDelta = radians(toLat - fromLat);
  const lngDelta = radians(toLng - fromLng);
  const calculation = Math.sin(latDelta / 2) ** 2
    + Math.cos(radians(fromLat)) * Math.cos(radians(toLat)) * Math.sin(lngDelta / 2) ** 2;
  return earthRadius * 2 * Math.atan2(Math.sqrt(calculation), Math.sqrt(1 - calculation));
}

function bearingDegrees(fromLat, fromLng, toLat, toLng) {
  const radians = value => value * Math.PI / 180;
  const lat1 = radians(fromLat);
  const lat2 = radians(toLat);
  const lngDelta = radians(toLng - fromLng);
  const y = Math.sin(lngDelta) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(lngDelta);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}

function angleDifference(left, right) {
  const difference = Math.abs(left - right) % 360;
  return Math.min(difference, 360 - difference);
}

function safeImageUrl(photo) {
  const candidates = [photo.imageProcUrl, photo.fileurlProc, photo.fileurlTh, photo.fileurlLTh, photo.fileurl];
  for (const candidate of candidates) {
    if (!candidate) continue;
    const expanded = String(candidate).replace("[[sizeprefix]]", "proc");
    try {
      const url = new URL(expanded);
      const trusted = url.protocol === "https:" && (
        url.hostname === "cdn.kartaview.org"
        || /^storage\d+\.(openstreetcam\.org|kartaview\.org)$/.test(url.hostname)
      );
      if (trusted) return url.toString();
    } catch (_error) {
      // Ignore malformed upstream URLs and preserve the existing cover.
    }
  }
  return "";
}

function sourceUrl(photo) {
  const sequenceId = String(photo.sequenceId || photo.sequence?.id || "").replace(/[^0-9]/g, "");
  const sequenceIndex = String(photo.sequenceIndex ?? 0).replace(/[^0-9]/g, "") || "0";
  return sequenceId ? `https://kartaview.org/details/${sequenceId}/${sequenceIndex}/track-info` : "https://kartaview.org/";
}

function chooseExteriorPhoto(photos, restaurantLat, restaurantLng) {
  return photos.flatMap(photo => {
    const photoLat = numeric(photo.lat ?? photo.matchLat);
    const photoLng = numeric(photo.lng ?? photo.matchLng);
    const heading = numeric(photo.heading);
    const fieldOfView = numeric(photo.fieldOfView) ?? 70;
    const projection = String(photo.projection || "").toUpperCase();
    const imageUrl = safeImageUrl(photo);
    if (photoLat === null || photoLng === null || heading === null || !imageUrl) return [];
    if (projection === "SPHERE" || fieldOfView > 180) return [];
    if (photo.visibility && photo.visibility !== "public") return [];
    if (photo.status && photo.status !== "active") return [];
    const distance = distanceMeters(photoLat, photoLng, restaurantLat, restaurantLng);
    const direction = angleDifference(heading, bearingDegrees(photoLat, photoLng, restaurantLat, restaurantLng));
    const allowedDirection = Math.min(80, Math.max(MAX_DIRECTION_DIFFERENCE, fieldOfView / 2 + 18));
    if (distance > MAX_DISTANCE_METERS || direction > allowedDirection) return [];
    return [{ photo, imageUrl, distance, direction }];
  }).sort((left, right) => left.distance - right.distance || left.direction - right.direction)[0] || null;
}

module.exports = async function handler(request, response) {
  if (request.method !== "GET") {
    response.setHeader("Allow", "GET");
    return response.status(405).json({ error: "Method not allowed" });
  }

  const latitude = numeric(request.query.lat);
  const longitude = numeric(request.query.lng);
  if (latitude === null || longitude === null || latitude < 41.8 || latitude > 42.9 || longitude < -71.6 || longitude > -70.5) {
    return response.status(400).json({ error: "Coordinates must be within the Boston area." });
  }

  try {
    const url = new URL(KARTAVIEW_PHOTO_API);
    url.searchParams.set("lat", String(latitude));
    url.searchParams.set("lng", String(longitude));
    url.searchParams.set("zoomLevel", "18");
    url.searchParams.set("radius", String(MAX_DISTANCE_METERS));
    url.searchParams.set("join", "sequence");
    url.searchParams.set("itemsPerPage", "60");
    url.searchParams.set("orderBy", "id");
    url.searchParams.set("orderDirection", "desc");
    const upstream = await fetch(url, { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(4500) });
    if (!upstream.ok) throw new Error(`KartaView returned ${upstream.status}`);
    const payload = await upstream.json();
    const photos = Array.isArray(payload?.result?.data) ? payload.result.data : [];
    const match = chooseExteriorPhoto(photos, latitude, longitude);
    response.setHeader("Cache-Control", "public, max-age=300, s-maxage=604800, stale-while-revalidate=2592000");
    if (!match) return response.status(200).json({ photo: null });
    const contributorId = String(match.photo.sequence?.userId || match.photo.userId || "").replace(/[^0-9]/g, "");
    return response.status(200).json({
      photo: {
        imageUrl: match.imageUrl,
        sourceUrl: sourceUrl(match.photo),
        provider: "KartaView",
        license: "CC BY-SA 4.0",
        contributor: contributorId ? `Contributor #${contributorId}` : "KartaView contributor",
        distanceMeters: Math.round(match.distance),
        capturedAt: match.photo.shotDate || match.photo.dateAdded || "",
      },
    });
  } catch (_error) {
    response.setHeader("Cache-Control", "public, max-age=60, s-maxage=300, stale-while-revalidate=3600");
    return response.status(200).json({ photo: null });
  }
};

module.exports.chooseExteriorPhoto = chooseExteriorPhoto;
