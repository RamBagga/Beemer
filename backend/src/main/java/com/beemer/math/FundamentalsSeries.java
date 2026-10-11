package com.beemer.math;

import java.time.LocalDate;
import java.time.YearMonth;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Company-page chart series from the fundamentals table. Mirrors the slices
 * analytics.fundamentals_metrics hands to the Streamlit company view.
 */
public final class FundamentalsSeries {
    private static final Pattern PERIOD = Pattern.compile("([A-Za-z]{3}) (\\d{4})");
    private static final Map<String, Integer> MONTHS = Map.ofEntries(
            Map.entry("jan", 1), Map.entry("feb", 2), Map.entry("mar", 3), Map.entry("apr", 4),
            Map.entry("may", 5), Map.entry("jun", 6), Map.entry("jul", 7), Map.entry("aug", 8),
            Map.entry("sep", 9), Map.entry("oct", 10), Map.entry("nov", 11), Map.entry("dec", 12));

    private FundamentalsSeries() {}

    public record Row(String section, String item, String period, double value) {}

    public record Point(Integer year, Double value) {}

    public record Charts(List<Point> sales, List<Point> profit, List<Point> opm, List<Point> roePct,
                         List<Point> roce, List<Point> peHist, List<Point> fcf) {}

    public static LocalDate periodEnd(String period) {
        if (period == null) return null;
        Matcher m = PERIOD.matcher(period.trim());
        if (!m.matches()) return null;
        Integer month = MONTHS.get(m.group(1).toLowerCase(Locale.ROOT));
        if (month == null) return null;
        return YearMonth.of(Integer.parseInt(m.group(2)), month).atEndOfMonth();
    }

    public static Charts charts(List<Row> rows, List<SeriesMath.Pt> closes) {
        Map<String, Map<String, Map<String, Double>>> tables = new LinkedHashMap<>();
        for (Row r : rows) {
            tables.computeIfAbsent(r.section(), k -> new LinkedHashMap<>())
                    .computeIfAbsent(r.period(), k -> new LinkedHashMap<>())
                    .put(r.item(), r.value());
        }
        Map<String, Map<String, Double>> pl = tables.getOrDefault("profit-loss", Map.of());
        List<LocalDate> years = new ArrayList<>();
        for (String period : pl.keySet()) {
            if ("TTM".equals(period)) continue;
            LocalDate d = periodEnd(period);
            if (d != null) years.add(d);
        }
        years.sort(Comparator.naturalOrder());

        List<Point> sales = new ArrayList<>();
        List<Point> profit = new ArrayList<>();
        List<Point> opm = new ArrayList<>();
        List<SeriesMath.Pt> profitPts = new ArrayList<>();
        Map<LocalDate, Double> equity = equityByDate(tables.get("balance-sheet"));
        List<Point> roe = new ArrayList<>();
        Double prevEq = null;
        boolean seenEq = false;
        for (LocalDate d : years) {
            Map<String, Double> items = itemsOn(pl, d);
            Double salesV = first(items, "Sales", "Revenue");
            Double np = first(items, "Net Profit");
            Double op = first(items, "OPM %");
            sales.add(new Point(d.getYear(), salesV));
            profit.add(new Point(d.getYear(), np));
            opm.add(new Point(d.getYear(), op));
            if (np != null) profitPts.add(new SeriesMath.Pt(d, np));
            Double eq = equity.get(d);
            Double avg;
            if (eq == null) avg = null;
            else if (!seenEq) avg = eq;
            else if (prevEq == null) avg = eq;
            else avg = (eq + prevEq) / 2.0;
            if (eq != null) {
                seenEq = true;
                prevEq = eq;
            } else prevEq = null;
            Double roeV = null;
            if (np != null && avg != null && avg > 0) roeV = np / avg * 100.0;
            roe.add(new Point(d.getYear(), roeV));
        }

        List<Point> roce = namedSeries(tables.get("ratios"), "ROCE %");
        List<Point> fcf = namedSeries(tables.get("cash-flow"), "Free Cash Flow");
        List<Point> pe = pePoints(pl, closes, profitPts);
        return new Charts(sales, profit, opm, roe, roce, pe, fcf);
    }

    private static List<Point> pePoints(Map<String, Map<String, Double>> pl, List<SeriesMath.Pt> closes, List<SeriesMath.Pt> profitPts) {
        Map<String, Double> ttm = pl.get("TTM");
        if (ttm == null && !pl.isEmpty()) {
            String last = null;
            for (String k : pl.keySet()) last = k;
            ttm = last == null ? null : pl.get(last);
        }
        if (ttm == null) return List.of();
        Double eps = ttm.get("EPS in Rs");
        Double np = ttm.get("Net Profit");
        if (eps == null || np == null || eps <= 0 || np <= 0) return List.of();
        PeHistory.Result hist = PeHistory.compute(closes, profitPts, np, eps);
        List<Point> out = new ArrayList<>();
        for (PeHistory.Hist h : hist.points()) out.add(new Point(h.date().getYear(), h.pe()));
        return out;
    }

    private static List<Point> namedSeries(Map<String, Map<String, Double>> section, String item) {
        if (section == null) return List.of();
        List<Point> out = new ArrayList<>();
        List<String> periods = new ArrayList<>(section.keySet());
        periods.sort(Comparator.comparing(p -> {
            LocalDate d = periodEnd(p);
            return d == null ? LocalDate.MAX : d;
        }));
        for (String period : periods) {
            LocalDate d = periodEnd(period);
            if (d == null) continue;
            Double v = section.get(period).get(item);
            if (v == null) continue;
            out.add(new Point(d.getYear(), v));
        }
        return out;
    }

    private static Map<LocalDate, Double> equityByDate(Map<String, Map<String, Double>> bs) {
        Map<LocalDate, Double> out = new TreeMap<>();
        if (bs == null) return out;
        boolean hasCapital = bs.values().stream().anyMatch(m -> m.containsKey("Equity Capital"));
        boolean hasReserves = bs.values().stream().anyMatch(m -> m.containsKey("Reserves"));
        for (var e : bs.entrySet()) {
            LocalDate d = periodEnd(e.getKey());
            if (d == null) continue;
            Double capital = hasCapital ? e.getValue().get("Equity Capital") : 0.0;
            Double reserves = hasReserves ? e.getValue().get("Reserves") : 0.0;
            if (capital == null || reserves == null) continue;
            out.put(d, capital + reserves);
        }
        return out;
    }

    private static Map<String, Double> itemsOn(Map<String, Map<String, Double>> pl, LocalDate date) {
        for (var e : pl.entrySet()) {
            LocalDate d = periodEnd(e.getKey());
            if (date.equals(d)) return e.getValue();
        }
        return Map.of();
    }

    private static Double first(Map<String, Double> items, String... names) {
        for (String n : names) if (items.containsKey(n)) return items.get(n);
        return null;
    }
}
