export function GET() {
  return Response.json({ status: "ok", service: "frontend", version: "0.1.0" });
}
