import http from "node:http";
import { HealthService } from "./services/health.js";
const health = new HealthService();
const server = http.createServer(async (request, response) => {
  if (request.url === "/health") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify(await health.basic()));
    return;
  }
  response.writeHead(404).end();
});
server.listen(Number(process.env.PORT ?? 4100), "127.0.0.1");
