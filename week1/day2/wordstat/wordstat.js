#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { Worker } = require("worker_threads");

const args = process.argv.slice(2);

let file = null;
let top = 10;
let minLen = 1;
let unique = false;
let concurrency = 1;

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--file") file = args[++i];
  else if (args[i] === "--top") top = Number(args[++i]);
  else if (args[i] === "--minLen") minLen = Number(args[++i]);
  else if (args[i] === "--unique") unique = true;
  else if (args[i] === "--concurrency") concurrency = Number(args[++i]);
}

const fileSize = fs.statSync(file).size;
const chunkSize = Math.ceil(fileSize / concurrency);

function runWorker(start, end) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(path.join(__dirname, "worker.js"), {
      workerData: { file, start, end, minLen }
    });
    worker.on("message", resolve);
    worker.on("error", reject);
  });
}

(async () => {
  const startTime = process.hrtime.bigint();

  const workers = [];
  for (let i = 0; i < concurrency; i++) {
    const start = i * chunkSize;
    const end = Math.min(fileSize, start + chunkSize);
    workers.push(runWorker(start, end));
  }

  const results = await Promise.all(workers);

  const globalFreq = new Map();
  let totalWords = 0;
  let longest = "";
  let shortest = null;

  for (const r of results) {
    totalWords += r.total;

    if (r.longest.length > longest.length) longest = r.longest;
    if (!shortest || (r.shortest && r.shortest.length < shortest.length)) {
      shortest = r.shortest;
    }

    for (const [word, count] of Object.entries(r.freq)) {
      globalFreq.set(word, (globalFreq.get(word) || 0) + count);
    }
  }

  const topWords = [...globalFreq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, top);

  const stats = {
    totalWords,
    uniqueWords: unique ? globalFreq.size : undefined,
    longestWord: longest,
    shortestWord: shortest,
    topWords
  };

  fs.mkdirSync("output", { recursive: true });
  fs.writeFileSync("output/stats.json", JSON.stringify(stats, null, 2));

  const endTime = process.hrtime.bigint();
  const durationMs = Number(endTime - startTime) / 1e6;

  console.log(`Completed in ${durationMs.toFixed(2)} ms`);
})();


if (!file) {
  console.error("Missing --file");
  process.exit(1);
}
