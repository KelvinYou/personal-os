import { NextResponse } from "next/server";
import {
  addPortfolioPosition,
  deletePortfolioPosition,
  savePortfolioField,
} from "@/lib/finance-edit";

interface PatchBody {
  market?: "US" | "MY";
  symbol?: string;
  fields?: Record<string, string>;
}

function badMarket(market: unknown): market is "US" | "MY" {
  return market === "US" || market === "MY";
}

export async function PATCH(request: Request) {
  let body: PatchBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { market, symbol, fields } = body;
  if (!market || !symbol || !fields || Object.keys(fields).length === 0) {
    return NextResponse.json(
      { ok: false, error: "缺少 market / symbol / fields" },
      { status: 400 },
    );
  }
  if (!badMarket(market)) {
    return NextResponse.json({ ok: false, error: "market 必须是 US 或 MY" }, { status: 400 });
  }

  const result = await savePortfolioField(market, symbol, fields);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function POST(request: Request) {
  let body: PatchBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { market, symbol, fields } = body;
  if (!market || !symbol || !fields) {
    return NextResponse.json(
      { ok: false, error: "缺少 market / symbol / fields" },
      { status: 400 },
    );
  }
  if (!badMarket(market)) {
    return NextResponse.json({ ok: false, error: "market 必须是 US 或 MY" }, { status: 400 });
  }

  const result = await addPortfolioPosition(market, symbol, fields);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function DELETE(request: Request) {
  let body: { market?: "US" | "MY"; symbol?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { market, symbol } = body;
  if (!market || !symbol) {
    return NextResponse.json({ ok: false, error: "缺少 market / symbol" }, { status: 400 });
  }
  if (!badMarket(market)) {
    return NextResponse.json({ ok: false, error: "market 必须是 US 或 MY" }, { status: 400 });
  }

  const result = await deletePortfolioPosition(market, symbol);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
