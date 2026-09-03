// Network/media substitutes only; no browser profile or formal answer access.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../src/defense_mvp/annotation_playback.js'), 'utf8');

class Video extends EventTarget {
  constructor(id) { super(); this.id = id; this.readyState = 0; this.error = null; }
  set src(value) { this.currentSrc = value; }
  pause() { this.paused = true; }
  removeAttribute() { this.currentSrc = ''; }
  load() {}
  emit(name) { this.dispatchEvent(new Event(name)); }
}
function setup(fetcher, options = {}) {
  const blobs = new Map(), revoked = [], changes = [];
  const Media = vm.runInNewContext(source + '\nReviewMediaLoader', {
    fetch: fetcher, AbortController, Blob, setTimeout, clearTimeout,
    URL: {createObjectURL(blob) { const key = 'blob:' + blobs.size; blobs.set(key, blob); return key; }, revokeObjectURL(url) { revoked.push(url); }},
  });
  const videos = ['source', 'A', 'B'].map(id => new Video(id));
  const loader = new Media(videos, states => changes.push(JSON.parse(JSON.stringify(states))), options);
  return {loader, videos, blobs, revoked, changes, paths: {source: '/source', A: '/A', B: '/B'}};
}
function response(bytes = [1, 2, 3, 4], headers = {}) {
  return new Response(new Uint8Array(bytes), {headers: {'Content-Type': 'video/webm', 'Content-Length': String(bytes.length), ...headers}});
}

test('authenticated complete bytes, progress, playback gate and URL cleanup', async () => {
  const h = setup(async (url, options) => {
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    return response();
  });
  try {
    await h.loader.start(h.paths);
    assert.equal(h.blobs.size, 3);
    for (const blob of h.blobs.values()) assert.deepEqual([...new Uint8Array(await blob.arrayBuffer())], [1, 2, 3, 4]);
    assert.ok(h.changes.some(s => s.source.bytes === 4));
    for (const v of h.videos) {
      assert.equal(h.loader.states[v.id].loaded, false);
      v.readyState = 4; v.emit('canplay');
      assert.equal(h.loader.states[v.id].loaded, true);
      assert.equal(h.loader.states[v.id].played, false);
      v.emit('playing');
      assert.equal(h.loader.states[v.id].played, true);
    }
  } finally { h.loader.dispose(); }
  assert.equal(h.revoked.length, 3);
});

test('403 is visible and never retried or exposed as playable', async () => {
  let calls = 0;
  const h = setup(async () => { calls++; return new Response('{}', {status: 403}); });
  await h.loader.start(h.paths);
  assert.equal(calls, 3); assert.equal(h.blobs.size, 0);
  assert.ok(Object.values(h.loader.states).every(s => s.phase === 'error' && !s.played && s.message.includes('会话失效')));
  h.loader.dispose();
});

test('one bounded network retry can recover', async () => {
  const counts = {};
  const h = setup(async url => { counts[url] = (counts[url] || 0) + 1; if (counts[url] === 1) throw new TypeError('Failed to fetch'); return response(); });
  await h.loader.start(h.paths);
  assert.deepEqual(Object.values(counts), [2, 2, 2]);
  assert.equal(h.blobs.size, 3);
  h.loader.dispose();
});

test('unexpected transport diagnostics do not leak URLs or local paths', async () => {
  const h = setup(async () => { throw new Error('private file D:/example token=secret'); });
  await h.loader.start(h.paths);
  assert.ok(Object.values(h.loader.states).every(s => s.message === '连接失败，请重新加载'));
  h.loader.dispose();
});

test('truncated, overlong, too large and non-video responses never create URLs', async () => {
  for (const headers of [{'Content-Length': '5'}, {'Content-Length': '3'}, {'Content-Length': '999'}, {'Content-Type': 'application/json'}]) {
    let calls = 0;
    const h = setup(async () => { calls++; return response([1, 2, 3, 4], headers); }, {maxBytes: 10});
    await h.loader.start(h.paths);
    assert.equal(h.blobs.size, 0); assert.ok(calls <= 6);
    assert.ok(Object.values(h.loader.states).every(s => s.phase === 'error'));
    h.loader.dispose();
  }
});

test('stalled connection times out twice then leaves actionable errors', async () => {
  let calls = 0;
  const h = setup((url, {signal}) => new Promise((resolve, reject) => { calls++; signal.addEventListener('abort', () => reject(new Error('aborted')), {once: true}); }), {timeoutMs: 15});
  await h.loader.start(h.paths);
  assert.equal(calls, 6);
  assert.ok(Object.values(h.loader.states).every(s => s.message.includes('读取超时')));
  h.loader.dispose();
});

test('timeout also covers a stalled response body', async () => {
  const h = setup(async (url, {signal}) => new Response(new ReadableStream({start(controller) { signal.addEventListener('abort', () => controller.error(new Error('aborted')), {once: true}); }}), {headers: {'Content-Type': 'video/webm', 'Content-Length': '4'}}), {timeoutMs: 15});
  await h.loader.start(h.paths);
  assert.ok(Object.values(h.loader.states).every(s => s.message.includes('读取超时')));
  assert.equal(h.blobs.size, 0);
  h.loader.dispose();
});

test('cancelled generation ignores late responses and old events', async () => {
  const resolve = [];
  const h = setup(() => new Promise(r => resolve.push(r)));
  const loading = h.loader.start(h.paths);
  h.loader.dispose();
  const count = h.changes.length;
  resolve.forEach(r => r(response()));
  await loading;
  for (const v of h.videos) { v.readyState = 4; v.emit('canplay'); v.emit('playing'); }
  assert.equal(h.blobs.size, 0); assert.equal(h.changes.length, count);
});

test('decode failure stays blocked even if a late canplay follows', async () => {
  const h = setup(async () => response());
  await h.loader.start(h.paths);
  const v = h.videos[1];
  v.error = {code: 4}; v.emit('error'); v.readyState = 4; v.emit('canplay'); v.emit('playing');
  assert.equal(h.loader.states.A.phase, 'error'); assert.equal(h.loader.states.A.played, false);
  h.loader.dispose();
});

test('decode stall is reported instead of waiting forever', async () => {
  const h = setup(async () => response(), {timeoutMs: 15});
  await h.loader.start(h.paths);
  await new Promise(r => setTimeout(r, 30));
  assert.ok(Object.values(h.loader.states).every(s => s.phase === 'error' && s.message.includes('解码超时')));
  h.loader.dispose();
});
