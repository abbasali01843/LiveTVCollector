const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

function loadConfig() {
  const cfg = {
    concurrency: 24,
    fetchTimeout: 15000,
    linkCheckTimeout: 8000,
    batchSize: 100,
    outputDirPrefix: 'SpecialLinks',
    channelsPerFile: 2000
  };
  try {
    const text = fsSync.readFileSync('config.yml', 'utf8');
    for (const line of text.split(/\r?\n/)) {
      const num = line.match(/^\s*(concurrency|fetchTimeout|linkCheckTimeout|batchSize|channelsPerFile)\s*:\s*(\d+)\s*$/);
      if (num) { cfg[num[1]] = Math.max(1, parseInt(num[2], 10)); continue; }
      const str = line.match(/^\s*outputDirPrefix\s*:\s*([A-Za-z0-9_-]+)\s*$/);
      if (str) cfg.outputDirPrefix = str[1];
    }
  } catch { /* fall back to defaults when config.yml is absent */ }
  return cfg;
}

const CONFIG = loadConfig();
const OUTPUT = CONFIG.outputDirPrefix;
const CHANNELS_PER_FILE = CONFIG.channelsPerFile;

function sourceUrls() {
  const raw = process.env.SPECIAL_M3U_URLS || '';
  return raw.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
}

async function fetchText(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), CONFIG.fetchTimeout);
  try {
    const response = await fetch(url, {
      redirect: 'follow',
      signal: controller.signal,
      headers: { 'user-agent': 'LiveTVCollector-Special/2.3' }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return { text: await response.text(), finalUrl: response.url };
  } finally {
    clearTimeout(timer);
  }
}

function attrs(line) {
  const out = {};
  for (const match of line.matchAll(/([\w-]+)="([^"]*)"/g)) out[match[1]] = match[2];
  return out;
}

function parseM3U(text, source) {
  const result = [];
  let pending = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('#EXTINF:')) {
      const a = attrs(line);
      pending = {
        name: line.includes(',') ? line.split(',').slice(1).join(',').trim() : 'Unnamed Channel',
        group: a['group-title'] || 'Uncategorized',
        country: a['tvg-country'] || 'Unknown',
        logo: a['tvg-logo'] || '',
        attrs: a
      };
    } else if (/^https?:\/\//i.test(line) && pending) {
      result.push({ ...pending, url: line, source });
      pending = null;
    }
  }
  return result;
}

function parseJson(text, source) {
  let data;
  try { data = JSON.parse(text); } catch { return []; }
  if (data && !Array.isArray(data)) {
    for (const key of ['channels', 'items', 'data', 'streams', 'results']) {
      if (Array.isArray(data[key])) { data = data[key]; break; }
    }
  }
  if (!Array.isArray(data)) return [];
  return data.flatMap(item => {
    if (!item || typeof item !== 'object') return [];
    const url = item.url || item.stream_url || item.streamUrl || item.link || item.stream;
    if (typeof url !== 'string' || !/^https?:\/\//i.test(url)) return [];
    return [{
      name: String(item.name || item.title || item.channel || 'Unnamed Channel'),
      group: String(item.group || item['group-title'] || item.category || 'Uncategorized'),
      country: String(item.country || 'Unknown'),
      logo: String(item.logo || item.img || item['tvg-logo'] || item.image || ''),
      url, source
    }];
  });
}

function classify(ch) {
  const text = `${ch.group} ${ch.country}`.toLowerCase();
  const known = ['usa','india','uk','canada','australia','germany','france','italy','spain','brazil','china','japan','korea','mexico','russia','south africa','argentina','netherlands','sweden','norway','bangladesh','turkey','indonesia','israel','portugal','peru','nepal','egypt','bahrain','venezuela'];
  const found = known.find(c => text.includes(c));
  return { group: ch.group || 'Uncategorized', country: found || ch.country || 'Unknown' };
}

async function fetchWithTimeout(url, options, ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function probe(url) {
  const headers = { 'user-agent': 'LiveTVCollector-Special/2.3' };
  try {
    const r = await fetchWithTimeout(url, { method: 'HEAD', redirect: 'follow', headers }, CONFIG.linkCheckTimeout);
    if (r.status >= 200 && r.status < 400) return true;
  } catch {}
  try {
    const r = await fetchWithTimeout(url, { redirect: 'follow', headers }, CONFIG.linkCheckTimeout);
    return r.status >= 200 && r.status < 400;
  } catch { return false; }
}

async function main() {
  const urls = sourceUrls();
  if (!urls.length) {
    console.log('SPECIAL_M3U_URLS is not configured; nothing to collect.');
    return;
  }

  const map = new Map();
  for (const source of urls) {
    try {
      const { text, finalUrl } = await fetchText(source);
      const lower = finalUrl.toLowerCase().split('?')[0];
      const items = lower.endsWith('.json') || text.trim().startsWith('{') || text.trim().startsWith('[')
        ? parseJson(text, finalUrl)
        : parseM3U(text, finalUrl);
      for (const ch of items) if (!map.has(ch.url)) map.set(ch.url, ch);
      console.log(`${source}: ${items.length} entries`);
    } catch (e) { console.warn(`${source}: ${e.message}`); }
  }

  const channels = [...map.values()];
  const active = [];
  const step = Math.max(1, Math.min(CONFIG.batchSize, 500));
  const parallel = Math.max(1, Math.min(CONFIG.concurrency, step));
  for (let i = 0; i < channels.length; i += step) {
    const batch = channels.slice(i, i + step);
    for (let j = 0; j < batch.length; j += parallel) {
      const slice = batch.slice(j, j + parallel);
      const results = await Promise.all(slice.map(async ch => [ch, await probe(ch.url)]));
      for (const [ch, ok] of results) if (ok) active.push(ch);
    }
  }

  await fs.rm(OUTPUT, { recursive: true, force: true });
  const grouped = new Map();
  for (const ch of active) {
    const c = classify(ch);
    const key = `${c.group}\0${c.country}`;
    if (!grouped.has(key)) grouped.set(key, { ...c, channels: [] });
    grouped.get(key).channels.push(ch);
  }

  const esc = s => String(s).replace(/"/g, '&quot;').replace(/[\r\n]+/g, ' ');
  // NOTE: dots are intentionally stripped so hostile group/country names
  // cannot escape OUTPUT via ".." path traversal.
  const safe = s => String(s).replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+/g, '').slice(0, 80) || 'Unknown';
  for (const { group, country, channels: list } of grouped.values()) {
    const dir = path.join(OUTPUT, safe(group), safe(country));
    await fs.mkdir(dir, { recursive: true });
    for (let i = 0; i < list.length; i += CHANNELS_PER_FILE) {
      const chunk = list.slice(i, i + CHANNELS_PER_FILE);
      const suffix = i === 0 ? '' : String(i / CHANNELS_PER_FILE + 1);
      const base = `SpecialLinks${suffix}`;
      const m3u = ['#EXTM3U'];
      for (const ch of chunk) m3u.push(`#EXTINF:-1 group-title="${esc(ch.group)}",${esc(ch.name)}`, ch.url);
      await Promise.all([
        fs.writeFile(path.join(dir, `${base}.m3u`), `${m3u.join('\n')}\n`),
        fs.writeFile(path.join(dir, `${base}.json`), JSON.stringify(chunk, null, 2)),
        fs.writeFile(path.join(dir, `${base}.txt`), chunk.map(c => c.url).join('\n'))
      ]);
    }
  }
  console.log(`Special collection complete: ${active.length} active / ${channels.length} unique.`);
}

main().catch(err => { console.error(err); process.exit(1); });
