import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const allowedHosts: string[] = JSON.parse(process.env.APP_ALLOWED_HOSTS ?? '["*"]');
  let hostname: string;
  try {
    hostname = new URL(`http://${request.headers.get("host") ?? ""}`).hostname.toLowerCase();
  } catch {
    return new NextResponse("Invalid host header", { status: 400 });
  }
  if (!allowedHosts.includes("*") && !allowedHosts.includes(hostname)) {
    return new NextResponse("Invalid host header", { status: 400 });
  }
  return NextResponse.next();
}
