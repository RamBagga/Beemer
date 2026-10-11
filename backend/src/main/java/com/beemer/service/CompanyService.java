package com.beemer.service;

import com.beemer.api.NotFoundException;
import com.beemer.data.MarketRepository;
import com.beemer.data.Metric;
import com.beemer.math.FundamentalsSeries;
import com.beemer.math.IndianFormat;
import com.beemer.math.SeriesMath;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

@Service
public class CompanyService {
    private static final Map<String, String> RADAR = Map.of(
            "roe", "QUALITY", "debt", "DEBT", "growth", "GROWTH", "moat", "MOAT", "fcf", "CASH", "value", "PRICE");
    private static final Map<String, String[]> EXPLAIN = Map.ofEntries(
            Map.entry("pe", new String[]{"P/E", "Price paid per ₹1 of yearly profit.", "A fair price for a great business beats a great price for a fair one."}),
            Map.entry("pb", new String[]{"P/B", "Price against book value per share.", "High P/B is fine when returns on that book are high."}),
            Map.entry("roe", new String[]{"ROE", "Profit per ₹100 of shareholders' capital.", "15%+, year after year, without heavy debt."}),
            Map.entry("roce", new String[]{"ROCE", "Operating profit per ₹100 of all capital, debt included.", "Tests the business, not its financing."}),
            Map.entry("de", new String[]{"Debt / equity", "Borrowings per ₹1 of shareholders' capital.", "Under 0.5 is comfortable."}),
            Map.entry("dy", new String[]{"Dividend yield", "Yearly dividend as a share of price.", "Cash returned when growth can't use it all."}),
            Map.entry("fcf", new String[]{"Free cash flow", "Cash left after running and investing in the business.", "A business is worth the cash it can return."}),
            Map.entry("opm", new String[]{"Operating margin", "Operating profit per ₹100 of sales.", "High and steady for years suggests a moat."}),
            Map.entry("max_drawdown", new String[]{"Max drawdown", "The deepest fall from a peak.", "Own it only if you could sit through a 50% fall."}),
            Map.entry("volatility", new String[]{"Volatility, 3 yrs", "How hard the price swings in a typical year.", "Swings are noise. Permanent loss is risk."}),
            Map.entry("iv", new String[]{"Value estimate", "Future earnings and dividends, discounted at 12% a year.", "Pay well below value."}),
            Map.entry("mos", new String[]{"Margin of safety", "Gap between price and value estimate. Positive is a cushion.", "Protection against being wrong."}));

    private final MetricsService metrics;
    private final PriceService prices;
    private final MarketRepository repo;

    public CompanyService(MetricsService metrics, PriceService prices, MarketRepository repo) {
        this.metrics = metrics;
        this.prices = prices;
        this.repo = repo;
    }

    @Cacheable("companies")
    public List<Map<String, Object>> list() {
        List<Metric> all = new ArrayList<>(metrics.all());
        all.sort(Comparator.comparing(m -> m.text("name") == null ? "" : m.text("name")));
        List<Map<String, Object>> out = new ArrayList<>();
        for (Metric m : all) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("symbol", m.symbol());
            row.put("name", m.text("name"));
            row.put("score", m.num("buffett_score"));
            out.add(row);
        }
        return out;
    }

    @Cacheable(value = "company", key = "#symbol")
    public Map<String, Object> company(String symbol) {
        List<Metric> all = metrics.all();
        Metric r = null;
        for (Metric m : all) if (symbol.equals(m.symbol())) r = m;
        if (r == null) throw new NotFoundException("No company " + symbol);
        List<JsonNode> subs = r.subscores();
        List<String> good = new ArrayList<>();
        List<String> bad = new ArrayList<>();
        List<Map<String, Object>> checks = new ArrayList<>();
        List<String> theta = new ArrayList<>();
        List<Double> radar = new ArrayList<>();
        for (JsonNode s : subs) {
            double pts = s.get("pts").asDouble();
            double max = s.get("max").asDouble();
            double f = max == 0 ? 0 : pts / max;
            String status = s.hasNonNull("status") ? s.get("status").asText() : (f >= 0.7 ? "pass" : f >= 0.4 ? "watch" : "fail");
            if ("pass".equals(status)) good.add(s.get("name").asText().toLowerCase());
            if ("fail".equals(status)) bad.add(s.get("name").asText().toLowerCase());
            Map<String, Object> c = new LinkedHashMap<>();
            c.put("status", status);
            c.put("name", s.get("name").asText());
            c.put("pts", pts);
            c.put("max", max);
            c.put("fraction", f);
            c.put("detail", s.get("detail").asText());
            c.put("why", s.get("why").asText());
            checks.add(c);
            String key = s.get("key").asText();
            theta.add(RADAR.getOrDefault(key, key.toUpperCase()));
            radar.add(f * 100);
        }
        String verdict = "";
        if (!good.isEmpty()) verdict += "Strong on " + String.join(", ", good) + ". ";
        if (!bad.isEmpty()) verdict += "Weak on " + String.join(", ", bad) + ". ";
        if (bad.isEmpty() && !good.isEmpty()) verdict += "No red flags.";

        boolean young = r.flag("young_listing");
        String first = r.text("first_date");
        String year = first == null ? "" : first.substring(0, 4);
        String youngNote = young ? "listed " + year : "data since " + year;

        Double cap = r.num("market_cap_cr");
        int higher = 0;
        if (cap != null) for (Metric m : all) {
            Double c = m.num("market_cap_cr");
            if (c != null && c > cap) higher++;
        }

        List<Map<String, Object>> kpis = new ArrayList<>();
        kpis.add(kpi("Price", IndianFormat.inr(r.num("price"), 0),
                fmtDate(r.text("last_date")) + ". 52-week high " + IndianFormat.inr(r.num("high_52w")) + "."));
        kpis.add(kpi("Market cap", IndianFormat.crore(cap), cap == null ? "" : "Rank " + (higher + 1) + " of " + all.size() + "."));
        if (r.num("pe") != null) {
            Double med = r.num("pe_median_10y");
            kpis.add(kpi("P/E", IndianFormat.num(r.num("pe")), med != null ? "10-yr median " + IndianFormat.num(med) + "." : EXPLAIN.get("pe")[1]));
        } else kpis.add(kpi("P/E", "n/m", "Not meaningful while loss-making."));
        Double roe = r.num("roe_median_10y");
        kpis.add(kpi("ROE · 10-yr median", IndianFormat.pct(roe, 0, false),
                "Latest " + IndianFormat.pct(r.num("roe_latest"), 0, false) + ". Target 15%+.",
                roe != null && roe >= 0.15 ? "pos" : "neg"));
        Double mos = r.num("margin_of_safety");
        kpis.add(kpi("Margin of safety", mos == null ? "n/m" : IndianFormat.pct(mos, 0, false),
                mos == null ? "No profit record to value." : "Value estimate " + IndianFormat.inr(r.num("intrinsic_value")) + ".",
                mos != null && mos > 0 ? "pos" : "neg"));

        List<Map<String, Object>> returns = new ArrayList<>();
        for (var lab : List.of(
                new String[]{"1 yr", "cagr_1y"}, new String[]{"3 yrs", "cagr_3y"}, new String[]{"5 yrs", "cagr_5y"},
                new String[]{"10 yrs", "cagr_10y"}, new String[]{"20 yrs", "cagr_20y"}, new String[]{"Since " + year, "cagr_max"})) {
            Double v = r.num(lab[1]);
            Map<String, Object> k = kpi(lab[0] + " / yr", v == null ? "–" : IndianFormat.pct(v), "");
            k.put("tone", v == null ? null : v > 0 ? "pos" : "neg");
            returns.add(k);
        }

        String about = repo.about(symbol);
        if (about != null) about = about.replaceAll("\\s*\\[\\d+\\]", "").trim();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("symbol", symbol);
        body.put("name", r.text("name"));
        body.put("subsector", r.text("subsector"));
        body.put("theme", r.text("theme"));
        body.put("youngNote", youngNote);
        body.put("score", r.num("buffett_score"));
        body.put("scoreLabel", r.text("score_label"));
        body.put("verdict", verdict.trim());
        body.put("young", young);
        body.put("profitable", r.flag("profitable_ttm"));
        if (young) {
            Double fy = r.num("fin_years");
            body.put("youngCallout", "<b>Young listing.</b> " + IndianFormat.fixed(r.num("history_years") == null ? 0 : r.num("history_years"), 1)
                    + " years of prices, " + (fy == null ? "few" : String.valueOf(fy.intValue())) + " years of results. Treat the score as provisional.");
        }
        if (!r.flag("profitable_ttm")) {
            body.put("lossCallout", "<b>Loss-making.</b> 12-month net profit " + IndianFormat.crore(r.num("profit_ttm_cr")) + ". Most tests read low until profits arrive.");
        }
        body.put("about", about == null || about.isBlank() ? null : about);
        body.put("kpis", kpis);
        body.put("checks", checks);
        body.put("radar", Map.of("theta", theta, "r", radar));
        body.put("returns", returns);
        body.put("prices", priceChart(symbol, r));
        body.put("fundamentals", fundamentals(symbol, r));
        body.put("metrics", keyMetrics(r));
        body.put("value", value(r));
        body.put("notes", notes(symbol, r));
        return body;
    }

    private Map<String, Object> priceChart(String symbol, Metric r) {
        List<SeriesMath.Pt> s = prices.adj(symbol);
        List<SeriesMath.Pt> sxAll = prices.adj("^BSESN");
        LocalDate start = s.get(0).date();
        List<SeriesMath.Pt> sx = new ArrayList<>();
        for (SeriesMath.Pt p : sxAll) if (!p.date().isBefore(start)) sx.add(p);
        List<Double> bench = new ArrayList<>();
        List<String> benchX = new ArrayList<>();
        double lo = s.stream().mapToDouble(SeriesMath.Pt::value).min().orElse(1);
        double hi = s.stream().mapToDouble(SeriesMath.Pt::value).max().orElse(1);
        if (!sx.isEmpty()) {
            double scale = s.get(0).value() / sx.get(0).value();
            for (SeriesMath.Pt p : sx) {
                double v = p.value() * scale;
                benchX.add(p.date().toString());
                bench.add(v);
                lo = Math.min(lo, v);
                hi = Math.max(hi, v);
            }
        }
        List<SeriesMath.Pt> dd = SeriesMath.drawdowns(s);
        Map<String, Object> chart = new LinkedHashMap<>();
        chart.put("x", s.stream().map(p -> p.date().toString()).toList());
        chart.put("price", s.stream().map(SeriesMath.Pt::value).toList());
        chart.put("benchX", benchX);
        chart.put("bench", bench);
        chart.put("dd", dd.stream().map(p -> p.value() * 100).toList());
        chart.put("yMin", lo);
        chart.put("yMax", hi);
        LocalDate ddDate = date(r.text("max_dd_date"));
        chart.put("caption", "Log scale vs Sensex, rebased. Worst fall <b>" + IndianFormat.fixed((r.num("max_drawdown") == null ? 0 : r.num("max_drawdown")) * 100, 0)
                + "%</b> (" + (ddDate == null ? "–" : IndianFormat.monthYear(ddDate)) + "). Now <b>"
                + IndianFormat.fixed((r.num("current_drawdown") == null ? 0 : r.num("current_drawdown")) * 100, 0)
                + "%</b> below peak. 3-yr volatility <b>" + IndianFormat.pct(r.num("volatility_3y"), 0, false) + "</b>.");
        return chart;
    }

    private Map<String, Object> fundamentals(String symbol, Metric r) {
        List<FundamentalsSeries.Row> rows = repo.fundamentals(symbol);
        FundamentalsSeries.Charts c = FundamentalsSeries.charts(rows, prices.close(symbol));
        Map<String, Object> f = new LinkedHashMap<>();
        boolean present = !c.sales().isEmpty();
        f.put("present", present);
        f.put("sales", c.sales());
        f.put("profit", c.profit());
        f.put("opm", c.opm());
        f.put("roePct", c.roePct());
        f.put("roce", c.roce());
        f.put("peHist", c.peHist());
        f.put("peToday", r.num("pe"));
        f.put("fcf", c.fcf());
        f.put("growthCaption", growthCaption(r));
        Double vs = r.num("pe_vs_history");
        f.put("peCaption", vs == null ? "Year-end P/E. Approximate."
                : "Year-end P/E vs today: <b>" + IndianFormat.fixed(Math.abs(vs) * 100, 0) + "% " + (vs < 0 ? "below" : "above") + "</b> the 10-yr median. Approximate.");
        f.put("peMissing", c.peHist().size() < 3);
        Double conv = r.num("fcf_conversion_10y");
        f.put("fcfCaption", conv == null ? "Cash conversion n/m." : "Cash conversion <b>" + IndianFormat.pct(conv, 0, false) + "</b> of profit, 10 years.");
        f.put("fcfMissing", c.fcf().isEmpty());
        if (!c.peHist().isEmpty()) {
            List<Double> pes = c.peHist().stream().map(FundamentalsSeries.Point::value).filter(v -> v != null).toList();
            f.put("peMedian", pes.isEmpty() ? null : SeriesMath.median(pes));
        }
        Map<String, Object> statement = profitLossGrid(rows);
        if (statement != null) f.put("statement", statement);
        return f;
    }

    /** Profit-and-loss line items down the side, financial years across. Same shape as Streamlit's annual dataframe transposed. */
    private static Map<String, Object> profitLossGrid(List<FundamentalsSeries.Row> rows) {
        Map<Integer, Map<String, Double>> byYear = new TreeMap<>();
        TreeSet<String> items = new TreeSet<>();
        for (FundamentalsSeries.Row row : rows) {
            if (!"profit-loss".equals(row.section())) continue;
            LocalDate end = FundamentalsSeries.periodEnd(row.period());
            if (end == null) continue;
            byYear.computeIfAbsent(end.getYear(), y -> new LinkedHashMap<>()).putIfAbsent(row.item(), row.value());
            items.add(row.item());
        }
        if (byYear.isEmpty()) return null;
        List<Integer> years = new ArrayList<>(byYear.keySet());
        List<Map<String, Object>> lines = new ArrayList<>();
        for (String item : items) {
            List<Double> vals = new ArrayList<>();
            for (Integer year : years) vals.add(byYear.get(year).get(item));
            Map<String, Object> line = new LinkedHashMap<>();
            line.put("item", item);
            line.put("values", vals);
            lines.add(line);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("years", years.stream().map(y -> "FY" + y).toList());
        out.put("rows", lines);
        return out;
    }

    private static String growthCaption(Metric r) {
        Integer per = null;
        for (int n : List.of(10, 5, 3)) if (r.num("sales_cagr_" + n + "y") != null) { per = n; break; }
        String g;
        if (per == null) g = "Too few years to measure growth. ";
        else {
            g = per + "-yr growth: sales <b>" + IndianFormat.pct(r.num("sales_cagr_" + per + "y")) + "</b>";
            Double pg = r.num("profit_cagr_" + per + "y");
            g += pg == null ? " a year. Profit growth n/m. " : ", profit <b>" + IndianFormat.pct(pg) + "</b> a year. ";
        }
        Double up = r.num("profit_up_years");
        Double checked = r.num("profit_years_checked");
        return g + "Profit up in <b>" + (up == null ? "–" : String.valueOf(up.intValue())) + "</b> of "
                + (checked == null ? "–" : String.valueOf(checked.intValue())) + " years.";
    }

    private static List<Map<String, Object>> keyMetrics(Metric r) {
        Double opm = r.num("opm_median_10y");
        Double fcf = r.num("fcf_latest_cr");
        List<String[]> items = List.of(
                new String[]{"pe", IndianFormat.num(r.num("pe"))},
                new String[]{"pb", IndianFormat.num(r.num("pb"))},
                new String[]{"roe", IndianFormat.pct(r.num("roe_median_10y"), 0, false) + " median"},
                new String[]{"roce", IndianFormat.pct(r.num("roce_median_10y"), 0, false) + " median"},
                new String[]{"de", IndianFormat.num(r.num("debt_to_equity"), 2)},
                new String[]{"dy", IndianFormat.pct(r.num("dividend_yield"), 2, false)},
                new String[]{"opm", opm == null ? "n/a" : IndianFormat.pct(opm, 0, false) + " median"},
                new String[]{"fcf", fcf == null ? "–" : IndianFormat.crore(fcf) + " (latest yr)"},
                new String[]{"max_drawdown", IndianFormat.pct(r.num("max_drawdown"), 0, false)},
                new String[]{"volatility", IndianFormat.pct(r.num("volatility_3y"), 0, false)},
                new String[]{"iv", IndianFormat.inr(r.num("intrinsic_value"))},
                new String[]{"mos", IndianFormat.pct(r.num("margin_of_safety"), 0, false)});
        List<Map<String, Object>> out = new ArrayList<>();
        for (String[] it : items) {
            String[] ex = EXPLAIN.get(it[0]);
            Map<String, Object> k = new LinkedHashMap<>();
            k.put("label", ex[0]);
            k.put("value", it[1]);
            k.put("expl", ex[1]);
            k.put("why", ex[2]);
            out.add(k);
        }
        return out;
    }

    private static Map<String, Object> value(Metric r) {
        Map<String, Object> v = new LinkedHashMap<>();
        Double iv = r.num("intrinsic_value");
        v.put("available", iv != null);
        if (iv == null) return v;
        v.put("eps", r.num("eps_ttm"));
        v.put("growth", r.num("iv_growth_used"));
        v.put("payout", r.num("iv_payout_used"));
        v.put("terminalPe", r.num("iv_terminal_pe"));
        v.put("value", iv);
        v.put("price", r.num("price"));
        v.put("mos", r.num("margin_of_safety"));
        return v;
    }

    private static Map<String, Object> notes(String symbol, Metric r) {
        Double fy0 = r.num("first_fy");
        Double fy1 = r.num("last_fy");
        String fetched = r.text("fund_fetched");
        Map<String, Object> n = new LinkedHashMap<>();
        n.put("prices", "Prices: " + r.text("first_date") + " to " + r.text("last_date") + ", Yahoo Finance " + symbol + ".NS.");
        n.put("fundamentals", "Fundamentals: screener.in, " + r.text("basis") + ", FY" + (fy0 == null ? "?" : fy0.intValue())
                + "–FY" + (fy1 == null ? "?" : fy1.intValue()) + "; refreshed " + (fetched == null ? "" : fetched.substring(0, Math.min(10, fetched.length()))) + ".");
        String clean = r.text("price_clean_notes");
        n.put("cleaning", "Price cleaning: " + (clean == null || clean.isBlank() ? "none" : clean) + ".");
        return n;
    }

    private static Map<String, Object> kpi(String label, String value, String expl) {
        return kpi(label, value, expl, null);
    }

    private static Map<String, Object> kpi(String label, String value, String expl, String tone) {
        Map<String, Object> k = new LinkedHashMap<>();
        k.put("label", label);
        k.put("value", value);
        k.put("expl", expl);
        k.put("tone", tone);
        return k;
    }

    private static String fmtDate(String iso) {
        if (iso == null || iso.length() < 10) return "–";
        return IndianFormat.dayMonthYear(LocalDate.parse(iso.substring(0, 10)));
    }

    private static LocalDate date(String iso) {
        if (iso == null || iso.length() < 10) return null;
        return LocalDate.parse(iso.substring(0, 10));
    }
}
