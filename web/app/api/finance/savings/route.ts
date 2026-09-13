import { NextResponse } from "next/server";
import {
  addSavingsAccount,
  deleteSavingsAccount,
  saveSavingsField,
} from "@/lib/finance-edit";

interface PatchBody {
  account?: string;
  fields?: Record<string, string>;
}

export async function PATCH(request: Request) {
  let body: PatchBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { account, fields } = body;
  if (!account || !fields || Object.keys(fields).length === 0) {
    return NextResponse.json(
      { ok: false, error: "缺少 account 或 fields" },
      { status: 400 },
    );
  }

  const result = await saveSavingsField(account, fields);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function POST(request: Request) {
  let body: PatchBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { account, fields } = body;
  if (!account || !fields) {
    return NextResponse.json(
      { ok: false, error: "缺少 account 或 fields" },
      { status: 400 },
    );
  }

  const result = await addSavingsAccount(account, fields);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}

export async function DELETE(request: Request) {
  let body: { account?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "请求体不是合法 JSON" }, { status: 400 });
  }

  const { account } = body;
  if (!account) {
    return NextResponse.json({ ok: false, error: "缺少 account" }, { status: 400 });
  }

  const result = await deleteSavingsAccount(account);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
