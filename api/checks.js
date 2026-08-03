const fallback = require("../data/checks.json");

const SHEET_URL = "https://docs.google.com/spreadsheets/d/1CwuBzDyTWOXvWgARrSqAxMH70xoxYaG-iWkYmOLRo5I/export?format=csv&gid=349385528";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (character === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some(value => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += character;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows.shift().map(value => value.replace(/^\uFEFF/, ""));
  return rows.map(values => Object.fromEntries(headers.map((header, index) => [header, values[index] || ""])));
}

function normalizedKey(value) {
  return String(value || "").trim().toLowerCase().replace(/[ _]/g, "");
}

function firstValue(row, candidates) {
  const normalized = Object.fromEntries(Object.entries(row).map(([key, value]) => [normalizedKey(key), value]));
  for (const candidate of candidates) {
    const value = normalized[normalizedKey(candidate)];
    if (value !== undefined && value !== "") return value;
  }
  return "";
}

function parseChecks(text) {
  return parseCsv(text).flatMap(row => {
    const restaurant = firstValue(row, ["restaurant", "レストラン", "店", "店舗"]);
    const rating = Number(firstValue(row, ["rating", "score", "your rating", "評価", "採点"]));
    if (!restaurant || !Number.isFinite(rating)) return [];
    const rawNote = firstValue(row, ["note", "notes", "comment", "explanation", "備考", "コメント"]);
    const relationshipLine = rawNote.split(/\r?\n/).find(line => line.startsWith("Relationship to cuisine:"));
    return [{
      timestamp: firstValue(row, ["timestamp", "time", "日時", "タイムスタンプ"]),
      country: firstValue(row, ["country", "home country", "国", "出身国"]),
      restaurant,
      rating,
      note: rawNote.split("\n\nRelationship to cuisine:", 1)[0].trim(),
      relationship: relationshipLine?.replace("Relationship to cuisine:", "").trim() || "Legacy HomeTaste check",
    }];
  });
}

module.exports = async function handler(_request, response) {
  try {
    const upstream = await fetch(SHEET_URL, { redirect: "follow", signal: AbortSignal.timeout(8000) });
    if (!upstream.ok) throw new Error(`Sheet returned ${upstream.status}`);
    const checks = parseChecks(await upstream.text());
    response.setHeader("Cache-Control", "public, s-maxage=300, stale-while-revalidate=3600");
    response.status(200).json({ source: "HomeTaste published Google Sheet", count: checks.length, checks });
  } catch (error) {
    response.setHeader("Cache-Control", "public, s-maxage=60, stale-while-revalidate=3600");
    response.status(200).json({ ...fallback, source: `${fallback.source} (snapshot fallback)`, warning: "Live checks were temporarily unavailable." });
  }
};
