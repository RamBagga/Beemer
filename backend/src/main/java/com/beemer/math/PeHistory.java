package com.beemer.math;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;

/**
 * Year-end P/E vs the stock's own history, the same formula as analytics.fundamentals_metrics:
 * last close on or before the year-end (within 15 days) × (TTM profit / TTM EPS) / that year's profit.
 */
public final class PeHistory {
    private PeHistory() {}

    public record Hist(LocalDate date, double pe) {}

    public record Result(List<Hist> points, Double median, Double vsHistory) {}

    public static Result compute(List<SeriesMath.Pt> closes, List<SeriesMath.Pt> annualProfit, double npTtm, double epsTtm) {
        if (epsTtm <= 0 || npTtm <= 0 || annualProfit.isEmpty()) return new Result(List.of(), null, null);
        List<SeriesMath.Pt> ordered = new ArrayList<>(closes);
        ordered.sort(java.util.Comparator.comparing(SeriesMath.Pt::date));
        closes = ordered;
        double shares = npTtm / epsTtm;
        List<SeriesMath.Pt> tail = annualProfit.size() <= 10 ? annualProfit : annualProfit.subList(annualProfit.size() - 10, annualProfit.size());
        List<Hist> vals = new ArrayList<>();
        for (SeriesMath.Pt profit : tail) {
            if (profit.value() <= 0) continue;
            SeriesMath.Pt last = null;
            for (SeriesMath.Pt c : closes) {
                if (!c.date().isAfter(profit.date())) last = c;
                else break;
            }
            if (last != null && ChronoUnit.DAYS.between(last.date(), profit.date()) < 15) {
                vals.add(new Hist(profit.date(), last.value() * shares / profit.value()));
            }
        }
        if (vals.size() < 3) return new Result(vals, null, null);
        Double med = SeriesMath.median(vals.stream().map(Hist::pe).toList());
        return new Result(vals, med, null);
    }

    public static Double vsHistory(Double peToday, Double median) {
        if (peToday == null || median == null || median == 0) return null;
        return peToday / median - 1;
    }
}
