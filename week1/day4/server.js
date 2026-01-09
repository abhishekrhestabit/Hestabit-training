const http = require("http");
const url = require("url");

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);

  if (parsedUrl.pathname === "/echo") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(req.headers, null, 2));
    return;
  }

  if (parsedUrl.pathname === "/slow") {
    const ms = parseInt(parsedUrl.query.ms || "1000", 10);
    setTimeout(() => {
      res.writeHead(200, { "Content-Type": "text/plain" });
      res.end(`Response delayed by ${ms} ms`);
    }, ms);
    return;
  }

  if (parsedUrl.pathname === "/cache") {
    res.writeHead(200, {
      "Content-Type": "application/json",
      "Cache-Control": "public, max-age=60",
      "ETag": "day4-cache-etag"
    });
    res.end(JSON.stringify({ message: "Cached response" }));
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

server.listen(3000, () => {
  console.log("Server running on http://localhost:3000");
});

