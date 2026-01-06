const fs = require("fs");
const path = require("path");

const LOG_DIR = path.join(__dirname, "logs");
const LOG_FILE = path.join(LOG_DIR, "day1-perf.json");
const TEST_FILE = "largefile.dat";

function formatMB(bytes) {
  return Number((bytes / (1024 * 1024)).toFixed(2));
}

function getMemory() {
  const mem = process.memoryUsage();
  return {
    rssMB: formatMB(mem.rss),
    heapUsedMB: formatMB(mem.heapUsed),
  };
}

function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

const result = {
  timestamp: new Date().toISOString(),
  bufferRead: {},
  streamRead: {},
};

// ---------------- BUFFER READ ----------------
const bufferStartMem = getMemory();
const bufferStartTime = process.hrtime.bigint();

fs.readFile(TEST_FILE, (err, data) => {
  if (err) throw err;

  const bufferEndTime = process.hrtime.bigint();
  const bufferEndMem = getMemory();

  result.bufferRead = {
    executionTimeMs: Number(bufferEndTime - bufferStartTime) / 1e6,
    memoryBefore: bufferStartMem,
    memoryAfter: bufferEndMem,
    fileSizeMB: formatMB(data.length),
  };

  // ---------------- STREAM READ ----------------
  const streamStartMem = getMemory();
  const streamStartTime = process.hrtime.bigint();

  let bytesRead = 0;
  const stream = fs.createReadStream(TEST_FILE);

  stream.on("data", chunk => {
    bytesRead += chunk.length;
  });

  stream.on("end", () => {
    const streamEndTime = process.hrtime.bigint();
    const streamEndMem = getMemory();

    result.streamRead = {
      executionTimeMs: Number(streamEndTime - streamStartTime) / 1e6,
      memoryBefore: streamStartMem,
      memoryAfter: streamEndMem,
      fileSizeMB: formatMB(bytesRead),
    };

    // ---------------- WRITE LOG ----------------
    ensureLogDir();

    let existingLogs = [];
    if (fs.existsSync(LOG_FILE)) {
      existingLogs = JSON.parse(fs.readFileSync(LOG_FILE, "utf-8"));
    }

    existingLogs.push(result);

    fs.writeFileSync(
      LOG_FILE,
      JSON.stringify(existingLogs, null, 2)
    );

    console.log("Performance log written to logs/day1-perf.json");
  });
});

