import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE?.replace("/api/1", "") || "http://dev.local:7000";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const contentType =
    request.headers.get("content-type") || "application/x-www-form-urlencoded";

  const backendResponse = await fetch(`${BACKEND_URL}/login/`, {
    method: "POST",
    headers: {
      "Content-Type": contentType,
      Cookie: request.headers.get("cookie") || "",
    },
    body,
    redirect: "manual",
  });

  const responseHeaders = new Headers();

  // Forward Set-Cookie headers from backend
  const setCookies = backendResponse.headers.getSetCookie();
  for (const cookie of setCookies) {
    responseHeaders.append("Set-Cookie", cookie);
  }

  // 302 = login succeeded (backend redirects to /)
  if (backendResponse.status === 302) {
    responseHeaders.set("Content-Type", "application/json");
    return NextResponse.json(
      { message: "Login successful", redirect: backendResponse.headers.get("location") || "/" },
      { status: 200, headers: responseHeaders }
    );
  }

  // 400 = validation error (wrong password, missing CSRF, etc.)
  const responseBody = await backendResponse.text();

  // Try to extract error from HTML form response
  const errorMatch = responseBody.match(/class="help-block">([^<]+)</);
  const errorMessage = errorMatch ? errorMatch[1].trim() : "Invalid credentials";

  responseHeaders.set("Content-Type", "application/json");
  return NextResponse.json(
    { message: errorMessage },
    { status: backendResponse.status, headers: responseHeaders }
  );
}
