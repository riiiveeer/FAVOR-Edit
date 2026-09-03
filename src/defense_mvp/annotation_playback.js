"use strict";

// Only current-question media is retained. No persistent browser cache or answers.
class ReviewMediaLoader {
  constructor(videos, changed, {timeoutMs = 20000, maxBytes = 64 * 1024 * 1024} = {}) {
    this.videos = videos;
    this.changed = changed;
    this.timeoutMs = timeoutMs;
    this.maxBytes = maxBytes;
    this.disposed = false;
    this.controllers = new Set();
    this.urls = new Set();
    this.timers = new Set();
    this.decodeTimers = new Map();
    this.events = new AbortController();
    this.states = Object.fromEntries(videos.map(v => [v.id, {phase: 'loading', bytes: 0, total: 0, loaded: false, played: false}]));
    for (const v of videos) {
      const options = {signal: this.events.signal};
      const loaded = () => {
        if (this.disposed || this.states[v.id].phase === 'error' || !this.urls.has(v.currentSrc) || v.readyState < 2) return;
        Object.assign(this.states[v.id], {phase: 'loaded', loaded: true});
        this.clearDecode(v.id);
        this.emit();
      };
      v.addEventListener('loadeddata', loaded, options);
      v.addEventListener('canplay', loaded, options);
      v.addEventListener('playing', () => {
        loaded();
        if (!this.states[v.id].loaded) return;
        this.states[v.id].played = true;
        this.emit();
      }, options);
      v.addEventListener('error', () => {
        if (v.error) this.fail(v.id, v.error.code === 3 || v.error.code === 4 ? '无法解码，请联系操作人员' : '播放失败，请重新加载');
      }, options);
    }
  }

  emit() { if (!this.disposed) this.changed(this.states); }
  clearDecode(id) {
    const timer = this.decodeTimers.get(id);
    clearTimeout(timer);
    this.timers.delete(timer);
    this.decodeTimers.delete(id);
  }
  fail(id, message) {
    if (this.disposed) return;
    this.clearDecode(id);
    Object.assign(this.states[id], {phase: 'error', loaded: false, played: false, message});
    this.videos.forEach(v => v.pause());
    this.emit();
  }

  async start(paths) {
    this.emit();
    await Promise.all(this.videos.map(v => this.load(v, paths[v.id])));
  }

  async load(v, path) {
    for (let attempt = 0; attempt < 2 && !this.disposed; attempt++) {
      const controller = new AbortController();
      this.controllers.add(controller);
      let timedOut = false;
      const timer = setTimeout(() => { timedOut = true; controller.abort(); }, this.timeoutMs);
      try {
        Object.assign(this.states[v.id], {phase: 'loading', bytes: 0, total: 0, attempt});
        this.emit();
        const response = await fetch(path, {credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal});
        if (response.status !== 200) {
          const error = new Error([403, 409].includes(response.status) ? '会话失效，请用当前启动链接恢复' : '媒体读取被拒绝，请联系操作人员');
          error.permanent = response.status < 500;
          throw error;
        }
        const type = response.headers.get('Content-Type') || '';
        const total = Number(response.headers.get('Content-Length'));
        if (!['video/webm', 'video/mp4'].includes(type) || !Number.isSafeInteger(total) || total <= 0 || total > this.maxBytes) {
          const error = new Error('媒体格式或大小异常，请联系操作人员');
          error.permanent = true;
          throw error;
        }
        this.states[v.id].total = total;
        const reader = response.body.getReader(), chunks = [];
        let received = 0;
        while (true) {
          const {value, done} = await reader.read();
          if (done) break;
          received += value.byteLength;
          if (received > total || received > this.maxBytes) throw new Error('媒体长度异常，请重新加载');
          chunks.push(value);
          this.states[v.id].bytes = received;
          this.emit();
        }
        if (received !== total) throw new Error('媒体读取不完整，请重新加载');
        if (this.disposed) return;
        const url = URL.createObjectURL(new Blob(chunks, {type}));
        this.urls.add(url);
        this.states[v.id].phase = 'decoding';
        this.emit();
        // Set src once. A second immediate load() can cancel the first request.
        v.src = url;
        const decodeTimer = setTimeout(() => {
          this.timers.delete(decodeTimer);
          if (!this.states[v.id].loaded) this.fail(v.id, '解码超时，请重新加载或联系操作人员');
        }, this.timeoutMs);
        this.timers.add(decodeTimer);
        this.decodeTimers.set(v.id, decodeTimer);
        return;
      } catch (error) {
        if (this.disposed) return;
        const known = ['会话失效，请用当前启动链接恢复', '媒体读取被拒绝，请联系操作人员', '媒体格式或大小异常，请联系操作人员', '媒体长度异常，请重新加载', '媒体读取不完整，请重新加载'];
        if (attempt === 1 || error.permanent) this.fail(v.id, timedOut ? '读取超时，请重新加载' : known.includes(error.message) ? error.message : '连接失败，请重新加载');
      } finally {
        clearTimeout(timer);
        controller.abort();
        this.controllers.delete(controller);
      }
      if (this.states[v.id].phase === 'error') return;
    }
  }

  dispose() {
    this.disposed = true;
    this.events.abort();
    this.controllers.forEach(c => c.abort());
    this.timers.forEach(t => clearTimeout(t));
    this.videos.forEach(v => { v.pause(); v.removeAttribute('src'); v.load(); });
    this.urls.forEach(url => URL.revokeObjectURL(url));
    this.urls.clear();
  }
}
