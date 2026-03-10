import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE?.replace("/api/1", "") || "http://dev.local:7000";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const contentType =
    request.headers.get("content-type") || "application/x-www-form-urlencoded";

  const backendResponse = await fetch(`${BACKEND_URL}/register/`, {
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

  // 302 = registration succeeded (backend redirects)
  if (backendResponse.status === 302) {
    const redirectLocation = backendResponse.headers.get("location") || "/";
    const requireEmailConfirmation =
      process.env.NEXT_PUBLIC_REQUIRE_EMAIL_CONFIRMATION === "true";

    responseHeaders.set("Content-Type", "application/json");
    return NextResponse.json(
      {
        status: "success",
        redirect: redirectLocation,
        requireEmailConfirmation,
      },
      { status: 200, headers: responseHeaders }
    );
  }

  // Error response — extract validation errors from HTML
  const responseBody = await backendResponse.text();

  const errors: string[] = [];
  const errorRegex = /class="help-block">([^<]+)/g;
  let match;
  while ((match = errorRegex.exec(responseBody)) !== null) {
    errors.push(match[1].trim());
  }

  const errorMessage = errors.length > 0 ? errors.join("; ") : "Registration failed";

  responseHeaders.set("Content-Type", "application/json");
  return NextResponse.json(
    { status: "error", error: errorMessage },
    { status: 400, headers: responseHeaders }
  );
}
