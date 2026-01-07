const { execSync } = require("child_process");
const fs = require("fs");

const levels = [1, 4, 8];
const results = [];

for (const level of levels) {
  const start = process.hrtime.bigint();

  execSync(
    `node wordstat.js --file corpus.txt --top 10 --minLen 5 --unique --concurrency ${level}`,
    { stdio: "ignore" }
  );

  const end = process.hrtime.bigint();

  results.push({
    concurrency: level,
    time_ms: Number(end - start) / 1e6
  });
}

fs.mkdirSync("logs", { recursive: true });
fs.writeFileSync("logs/perf-summary.json", JSON.stringify(results, null, 2));
