import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function myr(value: number): string {
  return `RM${value.toLocaleString("en-MY", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function pct(value: number, digits = 1): string {
  return `${value.toFixed(digits)}%`;
}

export function signedPct(value: number, digits = 1): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

/** Display names only; account identifiers remain unchanged in edit requests. */
export function accountLabel(key: string): string {
  const names: Record<string, string> = {
    gxbank: "GXBank FD", ryt_bank: "RYT Bank", boost_bank: "Boost Bank",
    tng_go_plus: "TNG GO+", maybank: "Maybank", moomoo_cash_myr: "moomoo · MYR cash",
    moomoo_cash_usd: "moomoo · USD cash", moomoo_fund: "moomoo · Cash fund",
  };
  if (names[key]) return names[key];
  if (key.startsWith("gxbank_fd_")) return `GXBank FD · ${key.slice(10).replaceAll("_", "-")}`;
  return key.replaceAll("_", " ");
}
