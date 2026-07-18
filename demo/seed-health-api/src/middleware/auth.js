export function requireAuthentication(request, response, next) {
  if (!request.headers.authorization) return response.writeHead(401).end();
  next();
}
