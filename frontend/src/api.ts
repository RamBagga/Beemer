const cache = new Map<string, Promise<unknown>>();

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    let message = r.statusText;
    try {
      const body = await r.json();
      if (body?.error) message = body.error;
    } catch { /* empty */ }
    throw new ApiError(r.status, message);
  }
  return r.json() as Promise<T>;
}

export function get<T>(path: string): Promise<T> {
  const hit = cache.get(path);
  if (hit) return hit as Promise<T>;
  const p = api<T>(path).catch((e) => {
    cache.delete(path);
    throw e;
  });
  cache.set(path, p);
  return p;
}

export function post<T>(path: string, body: unknown): Promise<T> {
  return api<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export interface Kpi { label: string; value: string; expl?: string; tone?: "pos" | "neg" | "acc" | null }
export interface Pt { year?: number; value: number | null }
export interface Series { name: string; color: string; dash?: string | null; width: number; fill?: boolean; x: string[]; y: number[] }

export interface Cockpit {
  companies: number;
  asOf: string | null;
  kpis: Kpi[];
  growth: { caption: string; yMin: number; yMax: number; series: Series[] };
  subsectors: { rows: SubRow[]; best: string; bestScore: number; worst: string; worstScore: number };
  listings: { bars: ListingBar[]; callout: string };
  rolling: { series: Series[]; table: { holding: string; periods: number; lost: string; beat: string; worst: string; median: string }[]; callout: string };
  drawdowns: { x: string[]; y: number[]; episodes: Episode[]; callout: string };
  sip: { options: SipOption[]; defaultSymbol: string; defaultYear: number; defaultAmount: number };
}
export interface SubRow { subsector: string; companies: number; score: number | null; profitable: number; roe: number | null; pe: number | null; cagr1: number | null; cagr3: number | null }
export interface ListingBar { symbol: string; label: string; name: string; subsector: string; firstDate: string; since: number; profitable: boolean }
export interface Episode { peak: string; bottom: string; fall: string; monthsDown: number | null; recovered: string; monthsRecover: number | null }
export interface SipOption { label: string; symbol: string; years: number[] }
export interface SipResult {
  invested: string; investedExpl: string; value: string; valueExpl: string; valueTone: string;
  xirr: string; xirrExpl: string; lump: string; lumpExpl: string; x: string[]; val: number[]; inv: number[];
}

export interface ScreenerRow {
  symbol: string; name: string; subsector: string; score: number | null; verdict: string | null;
  roeTest: number | null; debtTest: number | null; growthTest: number | null; moatTest: number | null; cashTest: number | null; priceTest: number | null;
  listed: number | null; profitable: boolean; roe: number | null; roce: number | null; debt: number | null;
  sales3: number | null; profit5: number | null; opm: number | null; pe: number | null; peVs: number | null; dy: number | null;
  mos: number | null; cagr1: number | null; cagr5: number | null; maxDd: number | null; mcap: number | null;
  tier?: "core" | "ext"; promoter?: number | null; fii?: number | null; deliv?: number | null;
}
export interface Screener {
  matches: number; score60: number; profitable: number; medianPe: number | null; callout: string;
  rows: ScreenerRow[]; scatter: { symbol: string; name: string; pe: number; roe: number; score: number | null; mcap: number | null }[];
  subsectors: string[];
  scope?: "core" | "all"; coreCount?: number; allCount?: number;
}

export interface PickCard {
  symbol: string; name: string; subsector: string | null; price: number; chg1d: number | null; score: number;
  buffettScore: number | null; reason: string; statLabel: string; stat: number | null; direction: string; rank: number; spark: number[];
}
export interface Belt {
  id: string; n: number; title: string; horizon: string; blurb: string; eligible: number | null; universe: number | null;
  previous: string[]; entered: string[]; names: Record<string, string>; note: string; cards: PickCard[];
}
export interface Picks { empty: boolean; updated?: string; run?: string; asOf?: string | null; belts?: Belt[]; trackRecord?: string | null }

export interface CompanyListItem { symbol: string; name: string; score: number | null; tier?: "core" | "ext" }

type Row = Record<string, string | number | null>;
export interface OwnershipRow { period: string; promoter: number | null; public: number | null; fii: number | null; dii: number | null; mf: number | null; insurance: number | null; retail: number | null; hni: number | null; pledge_flag: string | null; source: string }
export interface Filings {
  symbol: string;
  ownership: OwnershipRow[];
  dividends: { fy: string; year: number; perShare: number }[];
  dividendEvents: Row[];
  actions: { ex_date: string; subject: string; kind: string; ratio: string | null }[];
  nextMeeting: { meeting_date: string; purpose: string; description: string } | null;
  meetings: { meeting_date: string; purpose: string; description: string }[];
  insider: { person: string; category: string; txn_type: string; mode: string; qty: number | null; value: number | null; after_pct: number | null; to_date: string | null; disclosed_at: string | null }[];
  deals: { kind: string; date: string; client: string; side: string; qty: number | null; price: number | null }[];
  results: { basis: string; quarters: string[]; revenue: (number | null)[]; profit: (number | null)[]; margin: (number | null)[]; eps: (number | null)[]; revenueYoY?: number | null; profitYoY?: number | null };
  delivery: { date: string; close: number | null; volume: number | null; deliv_pct: number | null }[];
}
export interface MarketIndex { name: string; date: string; close: number | null; pct_change: number | null; pe: number | null; pb: number | null; div_yield: number | null; peMedian: number | null; historyFrom: string | null; change1y: number | null }
export interface Market { indices: MarketIndex[]; asOf: string | null }
export interface Check { status: string; name: string; pts: number; max: number; fraction: number; detail: string; why: string }
export interface Company {
  symbol: string; name: string; subsector: string; theme: string; youngNote: string; score: number | null; scoreLabel: string | null;
  verdict: string; young: boolean; profitable: boolean; about: string | null; youngCallout?: string; lossCallout?: string;
  kpis: Kpi[]; checks: Check[]; radar: { theta: string[]; r: number[] }; returns: Kpi[];
  prices: { x: string[]; price: number[]; benchX: string[]; bench: number[]; dd: number[]; yMin: number; yMax: number; caption: string };
  fundamentals: {
    present: boolean; sales: Pt[]; profit: Pt[]; opm: Pt[]; roePct: Pt[]; roce: Pt[]; peHist: Pt[]; peToday: number | null; fcf: Pt[];
    growthCaption: string; peCaption: string; peMissing: boolean; fcfCaption: string; fcfMissing: boolean; peMedian?: number | null;
    statement?: { years: string[]; rows: { item: string; values: (number | null)[] }[] };
  };
  metrics: { label: string; value: string; expl: string; why: string }[];
  value: { available: boolean; eps?: number; growth?: number; payout?: number; terminalPe?: number; value?: number; price?: number; mos?: number };
  notes: { prices: string; fundamentals: string; cleaning: string };
}
