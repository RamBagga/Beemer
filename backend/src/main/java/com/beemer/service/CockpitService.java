package com.beemer.service;

import com.beemer.data.Metric;
import com.beemer.math.IndianFormat;
import com.beemer.math.SeriesMath;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

@Service
public class CockpitService {
    private static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    private final MetricsService metrics;
    private final PriceService prices;

    public CockpitService(MetricsService metrics, PriceService prices) {
        this.metrics = metrics;
        this.prices = prices;
    }

    @Cacheable("cockpit")
    public Map<String, Object> view() {
        List<Metric> all = metrics.all();
        List<SeriesMath.Pt> it = prices.adj("^CNXIT");
        List<SeriesMath.Pt> nf = prices.adj("^NSEI");
        List<SeriesMath.Pt> sx = prices.adj("^BSESN");
        LocalDate start = it.get(0).date().isAfter(nf.get(0).date()) ? it.get(0).date() : nf.get(0).date();
        List<SeriesMath.Pt> nfSame = from(nf, start);

        int profitable = 0, young = 0, score60 = 0;
        LocalDate asOf = null;
        for (Metric m : all) {
            if (m.flag("profitable_ttm")) profitable++;
            if (m.flag("young_listing")) young++;
            Double sc = m.num("buffett_score");
            if (sc != null && sc >= 60) score60++;
            LocalDate d = date(m.text("last_date"));
            if (d != null && (asOf == null || d.isAfter(asOf))) asOf = d;
        }

        List<SeriesMath.Pt> dd = SeriesMath.drawdowns(it);
        double cur = dd.get(dd.size() - 1).value();
        LocalDate peakDate = it.stream().max(Comparator.comparingDouble(SeriesMath.Pt::value)).orElseThrow().date();

        List<Map<String, Object>> kpis = new ArrayList<>();
        kpis.add(kpi("Nifty IT · since " + it.get(0).date().getYear(),
                IndianFormat.pct(SeriesMath.cagr(it, null)) + "/yr",
                "Nifty 50: " + IndianFormat.pct(SeriesMath.cagr(nfSame, null)) + "/yr, same period.", "acc"));
        kpis.add(kpi("Sensex · since " + sx.get(0).date().getYear(),
                IndianFormat.pct(SeriesMath.cagr(sx, null)) + "/yr", "Excludes dividends.", null));
        kpis.add(kpi("Nifty IT vs peak", cur < -0.001 ? IndianFormat.pct(cur, 1, false) : "At a high",
                "Peak " + IndianFormat.monthYear(peakDate) + ".", cur < -0.1 ? "neg" : null));
        kpis.add(kpi("Companies", String.valueOf(all.size()),
                profitable + " profitable · " + young + " listed under 5 years.", null));
        kpis.add(kpi("Score 60+", String.valueOf(score60), "Of " + all.size() + " companies.", "pos"));

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("companies", all.size());
        body.put("asOf", asOf == null ? null : IndianFormat.dayMonthYear(asOf));
        body.put("kpis", kpis);
        body.put("growth", growth(Map.of("Sensex", sx, "Nifty 50", nf, "Nifty IT", it), start));
        body.put("subsectors", subsectors(all));
        body.put("listings", listings(all));
        body.put("rolling", rolling(it));
        body.put("drawdowns", drawdowns(it, dd));
        body.put("sip", sipDefaults(all, it, nf, sx));
        return body;
    }

    private Map<String, Object> growth(Map<String, List<SeriesMath.Pt>> idx, LocalDate start) {
        List<Map<String, Object>> series = new ArrayList<>();
        double hi = 4e4;
        for (String name : List.of("Sensex", "Nifty 50", "Nifty IT")) {
            List<SeriesMath.Pt> s = from(idx.get(name), start);
            double base = s.get(0).value();
            List<String> x = new ArrayList<>();
            List<Double> y = new ArrayList<>();
            for (SeriesMath.Pt p : s) {
                double v = 1e5 * p.value() / base;
                x.add(p.date().toString());
                y.add(v);
                hi = Math.max(hi, v);
            }
            Map<String, Object> line = new LinkedHashMap<>();
            line.put("name", name + "  " + IndianFormat.lakh(y.get(y.size() - 1)));
            line.put("color", name.equals("Sensex") ? "dim" : name.equals("Nifty 50") ? "violet" : "blue");
            line.put("dash", name.equals("Sensex") ? "dot" : null);
            line.put("width", name.equals("Nifty IT") ? 1.8 : 1.3);
            line.put("fill", name.equals("Nifty IT"));
            line.put("x", x);
            line.put("y", y);
            series.add(line);
        }
        Map<String, Object> g = new LinkedHashMap<>();
        g.put("caption", "₹1,00,000 invested " + IndianFormat.dayMonthYear(start) + ". Log scale. Excludes dividends, worth 1–2% a year.");
        g.put("yMin", 4e4);
        g.put("yMax", hi);
        g.put("series", series);
        return g;
    }

    private Map<String, Object> subsectors(List<Metric> all) {
        Map<String, List<Metric>> groups = new TreeMap<>();
        for (Metric m : all) {
            String s = m.text("subsector");
            if (s != null) groups.computeIfAbsent(s, k -> new ArrayList<>()).add(m);
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        for (var e : groups.entrySet()) {
            List<Metric> g = e.getValue();
            int prof = 0;
            for (Metric m : g) if (m.flag("profitable_ttm")) prof++;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("subsector", e.getKey());
            row.put("companies", g.size());
            row.put("score", med(g, "buffett_score"));
            row.put("profitable", prof / (double) g.size());
            row.put("roe", med(g, "roe_median_10y"));
            row.put("pe", med(g, "pe"));
            row.put("cagr1", med(g, "cagr_1y"));
            row.put("cagr3", med(g, "cagr_3y"));
            rows.add(row);
        }
        rows.sort(Comparator.comparingDouble((Map<String, Object> r) -> r.get("score") == null ? Double.NEGATIVE_INFINITY : (Double) r.get("score")).reversed());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("rows", rows);
        if (!rows.isEmpty()) {
            out.put("best", rows.get(0).get("subsector"));
            out.put("bestScore", rows.get(0).get("score"));
            out.put("worst", rows.get(rows.size() - 1).get("subsector"));
            out.put("worstScore", rows.get(rows.size() - 1).get("score"));
        }
        return out;
    }

    private Map<String, Object> listings(List<Metric> all) {
        List<Map<String, Object>> bars = new ArrayList<>();
        List<Double> up = new ArrayList<>();
        List<Double> prof = new ArrayList<>();
        List<Double> loss = new ArrayList<>();
        for (Metric m : all) {
            Double year = m.num("listing_year");
            if (year == null || year < 2019) continue;
            List<SeriesMath.Pt> px = prices.adj(m.symbol());
            if (px.size() < 2) continue;
            double since = px.get(px.size() - 1).value() / px.get(0).value() - 1;
            String name = m.text("name") == null ? m.symbol() : m.text("name").replaceAll(" \\(.*\\)", "");
            Map<String, Object> bar = new LinkedHashMap<>();
            bar.put("symbol", m.symbol());
            bar.put("label", name + "  " + year.intValue());
            bar.put("name", name);
            bar.put("subsector", m.text("subsector"));
            bar.put("firstDate", m.text("first_date"));
            bar.put("since", since);
            bar.put("profitable", m.flag("profitable_ttm"));
            bars.add(bar);
            up.add(since);
            (m.flag("profitable_ttm") ? prof : loss).add(since);
        }
        bars.sort(Comparator.comparingDouble(b -> (Double) b.get("since")));
        double upFrac = up.isEmpty() ? 0 : up.stream().filter(v -> v > 0).count() / (double) up.size();
        Double pu = prof.isEmpty() ? null : SeriesMath.median(prof);
        Double lu = loss.isEmpty() ? null : SeriesMath.median(loss);
        String callout = "<b>" + bars.size() + "</b> listings since 2019. <b>" + IndianFormat.fixed(upFrac * 100, 0)
                + "%</b> trade above their first close. Profitable: <b>" + IndianFormat.signed((pu == null ? 0 : pu) * 100, 0)
                + "%</b> median. Loss-making: <b>" + IndianFormat.signed((lu == null ? 0 : lu) * 100, 0) + "%</b>.";
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("bars", bars);
        out.put("callout", callout);
        return out;
    }

    private Map<String, Object> rolling(List<SeriesMath.Pt> it) {
        List<SeriesMath.Pt> me = SeriesMath.monthEndLast(it);
        Map<Integer, List<SeriesMath.Pt>> roll = new LinkedHashMap<>();
        for (int y : List.of(1, 3, 5, 10)) roll.put(y, SeriesMath.rollingCagr(me, y));
        List<Map<String, Object>> series = new ArrayList<>();
        for (int y : List.of(1, 5, 10)) {
            List<SeriesMath.Pt> r = roll.get(y);
            Map<String, Object> line = new LinkedHashMap<>();
            line.put("name", y + "-year holding");
            line.put("color", y == 1 ? "dim" : y == 5 ? "violet" : "blue");
            line.put("width", y == 1 ? 1.1 : y == 5 ? 1.4 : 2.0);
            line.put("x", r.stream().map(p -> p.date().toString()).toList());
            line.put("y", r.stream().map(p -> p.value() * 100).toList());
            series.add(line);
        }
        List<Map<String, Object>> table = new ArrayList<>();
        for (var e : roll.entrySet()) {
            List<SeriesMath.Pt> r = e.getValue();
            List<Double> vals = r.stream().map(SeriesMath.Pt::value).toList();
            double lost = r.stream().filter(p -> p.value() < 0).count() / (double) r.size();
            double beat = r.stream().filter(p -> p.value() > 0.10).count() / (double) r.size();
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("holding", e.getKey() + " yr");
            row.put("periods", r.size());
            row.put("lost", IndianFormat.fixed(lost * 100, 0) + "%");
            row.put("beat", IndianFormat.fixed(beat * 100, 0) + "%");
            row.put("worst", IndianFormat.pct(vals.stream().mapToDouble(Double::doubleValue).min().orElse(0)));
            row.put("median", IndianFormat.pct(SeriesMath.median(vals)));
            table.add(row);
        }
        List<SeriesMath.Pt> y1 = roll.get(1);
        List<SeriesMath.Pt> y10 = roll.get(10);
        double lost1 = y1.stream().filter(p -> p.value() < 0).count() / (double) y1.size();
        double lost10 = y10.stream().filter(p -> p.value() < 0).count() / (double) y10.size();
        double med10 = SeriesMath.median(y10.stream().map(SeriesMath.Pt::value).toList());
        String callout = "Held 1 year, Nifty IT lost money <b>" + IndianFormat.fixed(lost1 * 100, 0)
                + "%</b> of the time. Held 10 years: <b>" + IndianFormat.fixed(lost10 * 100, 0)
                + "%</b>. Median <b>" + IndianFormat.fixed(med10 * 100, 1) + "%</b> a year.";
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("series", series);
        out.put("table", table);
        out.put("callout", callout);
        return out;
    }

    private Map<String, Object> drawdowns(List<SeriesMath.Pt> it, List<SeriesMath.Pt> dd) {
        List<SeriesMath.Crash> eps = SeriesMath.crashes(it, -0.2);
        List<Map<String, Object>> rows = new ArrayList<>();
        SeriesMath.Crash worst = null;
        for (SeriesMath.Crash c : eps) {
            if (worst == null || c.fallPct() < worst.fallPct()) worst = c;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("peak", IndianFormat.monthYear(c.peak()));
            row.put("bottom", IndianFormat.monthYear(c.trough()));
            row.put("fall", IndianFormat.fixed(c.fallPct(), 0) + "%");
            row.put("monthsDown", c.monthsDown());
            row.put("recovered", c.recovery() == null ? "Not yet" : IndianFormat.monthYear(c.recovery()));
            row.put("monthsRecover", c.monthsRecover());
            rows.add(row);
        }
        String callout = worst == null ? "" : "<b>" + eps.size() + "</b> falls of 20%+ since " + it.get(0).date().getYear()
                + ". Deepest: <b>" + IndianFormat.fixed(worst.fallPct(), 0) + "%</b>, "
                + IndianFormat.monthYear(worst.peak()) + " to " + IndianFormat.monthYear(worst.trough()) + ".";
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("x", dd.stream().map(p -> p.date().toString()).toList());
        out.put("y", dd.stream().map(p -> p.value() * 100).toList());
        out.put("episodes", rows);
        out.put("callout", callout);
        return out;
    }

    private Map<String, Object> sipDefaults(List<Metric> all, List<SeriesMath.Pt> it, List<SeriesMath.Pt> nf, List<SeriesMath.Pt> sx) {
        List<Map<String, Object>> options = new ArrayList<>();
        options.add(optSeries("Nifty IT", "^CNXIT", it));
        options.add(optSeries("Nifty 50", "^NSEI", nf));
        options.add(optSeries("Sensex", "^BSESN", sx));
        List<Metric> named = new ArrayList<>(all);
        named.sort(Comparator.comparing(m -> m.text("name") == null ? "" : m.text("name")));
        int now = LocalDate.now(IST).getYear();
        for (Metric m : named) {
            int first = m.text("first_date") == null ? now : Integer.parseInt(m.text("first_date").substring(0, 4));
            options.add(opt(m.text("name") + " (" + m.symbol() + ")", m.symbol(), years(first, now)));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("options", options);
        out.put("defaultSymbol", "^CNXIT");
        out.put("defaultYear", 2015);
        out.put("defaultAmount", 10000);
        return out;
    }

    private static Map<String, Object> optSeries(String label, String symbol, List<SeriesMath.Pt> series) {
        return opt(label, symbol, years(series.get(0).date().getYear(), LocalDate.now(IST).getYear()));
    }

    private static Map<String, Object> opt(String label, String symbol, List<Integer> years) {
        Map<String, Object> o = new LinkedHashMap<>();
        o.put("label", label);
        o.put("symbol", symbol);
        o.put("years", years);
        return o;
    }

    private static List<Integer> years(int firstYear, int now) {
        List<Integer> ys = new ArrayList<>();
        for (int y = firstYear + 1; y < now; y++) ys.add(y);
        if (ys.isEmpty()) ys.add(firstYear);
        return ys;
    }

    private static List<SeriesMath.Pt> from(List<SeriesMath.Pt> s, LocalDate start) {
        List<SeriesMath.Pt> out = new ArrayList<>();
        for (SeriesMath.Pt p : s) if (!p.date().isBefore(start)) out.add(p);
        return out;
    }

    private static Double med(List<Metric> rows, String key) {
        List<Double> xs = new ArrayList<>();
        for (Metric m : rows) {
            Double v = m.num(key);
            if (v != null) xs.add(v);
        }
        if (xs.isEmpty()) return null;
        return SeriesMath.median(xs);
    }

    private static LocalDate date(String iso) {
        if (iso == null || iso.length() < 10) return null;
        return LocalDate.parse(iso.substring(0, 10));
    }

    private static Map<String, Object> kpi(String label, String value, String expl, String tone) {
        Map<String, Object> k = new LinkedHashMap<>();
        k.put("label", label);
        k.put("value", value);
        k.put("expl", expl);
        k.put("tone", tone);
        return k;
    }
}
