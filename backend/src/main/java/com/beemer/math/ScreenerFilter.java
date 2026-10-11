package com.beemer.math;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Screener filters from app/views/screener.py, including the same null handling. */
public final class ScreenerFilter {
    private ScreenerFilter() {}

    public record Row(String symbol, String subsector, Double score, Double pe, Double debt,
                      Double roe, boolean profitable, boolean young, Double mos) {}

    public record Query(List<String> subsector, int minScore, double maxPe, double maxDe,
                        int minRoe, boolean profitable, boolean seasoned, boolean belowValue) {
        public static Query defaults() {
            return new Query(List.of(), 0, 150, 2.0, 0, false, false, false);
        }
    }

    public static List<Row> apply(List<Row> rows, Query q) {
        List<Row> f = new ArrayList<>(rows);
        if (q.subsector() != null && !q.subsector().isEmpty()) {
            f.removeIf(r -> r.subsector() == null || !q.subsector().contains(r.subsector()));
        }
        f.removeIf(r -> (r.score() == null ? 0 : r.score()) < q.minScore());
        if (q.maxPe() < 150) f.removeIf(r -> r.pe() != null && r.pe() > q.maxPe());
        if (q.maxDe() < 2.0) f.removeIf(r -> r.debt() != null && r.debt() > q.maxDe());
        if (q.minRoe() > 0) {
            double floor = q.minRoe() / 100.0;
            f.removeIf(r -> (r.roe() == null ? -1 : r.roe()) < floor);
        }
        if (q.profitable()) f.removeIf(r -> !r.profitable());
        if (q.seasoned()) f.removeIf(Row::young);
        if (q.belowValue()) f.removeIf(r -> r.mos() == null || r.mos() <= 0);
        f.sort(Comparator.comparing((Row r) -> r.score() == null).thenComparing(r -> r.score() == null ? 0 : -r.score()));
        return f;
    }
}
