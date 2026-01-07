const fs = require("fs");
const { workerData, parentPort } = require("worker_threads");

const { file, start, end, minLen } = workerData;

const buffer = Buffer.alloc(end - start);
const fd = fs.openSync(file, "r");
fs.readSync(fd, buffer, 0, buffer.length, start);
fs.closeSync(fd);

const words = buffer.toString("utf-8").split(/\s+/);

const freq = {};
let total = 0;
let longest = "";
let shortest = null;

for (const w of words) {
  if (!w || w.length < minLen) continue;

  total++;
  freq[w] = (freq[w] || 0) + 1;

  if (w.length > longest.length) longest = w;
  if (!shortest || w.length < shortest.length) shortest = w;
}

parentPort.postMessage({
  freq,
  total,
  longest,
  shortest
});
