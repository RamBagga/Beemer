package com.beemer.math;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Request-time price maths ported from analytics.py: CAGR, drawdowns, crash episodes,
 * month-end rolling returns, SIP units and XIRR. Behaviour matches the Python functions
 * on the golden Nifty IT sample.
 */
public final class SeriesMath {
    private SeriesMath() {}

    public record Pt(LocalDate date, double value) {}

    public record Flow(LocalDate date, double amount) {}

    public record Crash(LocalDate peak, LocalDate trough, double fallPct, double monthsDown,
                        LocalDate recovery, Double monthsRecover) {}

    public record Sip(double invested, double value, int months, Double xirr, LocalDate start,
                      List<Pt> investedPath, List<Pt> valuePath) {}

    public static Double cagr(List<Pt> series, Integer years) {
        List<Pt> s = dropNonPositive(series);
        if (s.isEmpty()) return null;
        Pt end = s.get(s.size() - 1);
        Pt start;
        if (years == null) {
            start = s.get(0);
        } else {
            LocalDate target = end.date().minusYears(years);
            if (s.get(0).date().isAfter(target.plusDays(10))) return null;
            start = null;
            for (Pt p : s) {
                if (!p.date().isAfter(target)) start = p;
                else break;
            }
            if (start == null) return null;
        }
        double yrs = ChronoUnit.DAYS.between(start.date(), end.date()) / 365.25;
        if (yrs <= 0 || start.value() <= 0) return null;
        return Math.pow(end.value() / start.value(), 1.0 / yrs) - 1;
    }

    public static List<Pt> drawdowns(List<Pt> series) {
        List<Pt> out = new ArrayList<>(series.size());
        double peak = Double.NEGATIVE_INFINITY;
        for (Pt p : series) {
            peak = Math.max(peak, p.value());
            out.add(new Pt(p.date(), peak == 0 ? 0 : p.value() / peak - 1));
        }
        return out;
    }

    public static List<Crash> crashes(List<Pt> series, double threshold) {
        List<Pt> s = new ArrayList<>();
        for (Pt p : series) if (!Double.isNaN(p.value())) s.add(p);
        if (s.isEmpty()) return List.of();
        List<Pt> dd = drawdowns(s);
        List<Crash> eps = new ArrayList<>();
        boolean in = false;
        int start = 0;
        for (int i = 0; i < dd.size(); i++) {
            double v = dd.get(i).value();
            if (!in && v < 0) {
                in = true;
                start = i;
            }
            if (in && v == 0.0) {
                addCrash(eps, s, dd, start, i, i, threshold);
                in = false;
            }
        }
        if (in) addCrash(eps, s, dd, start, dd.size() - 1, -1, threshold);
        return eps;
    }

    private static void addCrash(List<Crash> eps, List<Pt> s, List<Pt> dd, int start, int endIncl, int recoveryIdx, double threshold) {
        int minI = start;
        for (int i = start; i <= endIncl; i++) if (dd.get(i).value() < dd.get(minI).value()) minI = i;
        if (dd.get(minI).value() > threshold) return;
        int peakIdx = start >= 1 ? start - 1 : start;
        LocalDate peak = s.get(peakIdx).date();
        LocalDate trough = s.get(minI).date();
        LocalDate rec = recoveryIdx >= 0 ? s.get(recoveryIdx).date() : null;
        double monthsDown = round1(ChronoUnit.DAYS.between(peak, trough) / 30.44);
        Double monthsRec = rec == null ? null : round1(ChronoUnit.DAYS.between(trough, rec) / 30.44);
        eps.add(new Crash(peak, trough, dd.get(minI).value() * 100, monthsDown, rec, monthsRec));
    }

    public static List<Pt> monthEndLast(List<Pt> series) {
        List<Pt> out = new ArrayList<>();
        YearMonth cur = null;
        Pt last = null;
        for (Pt p : series) {
            YearMonth ym = YearMonth.from(p.date());
            if (cur != null && !ym.equals(cur)) {
                out.add(new Pt(cur.atEndOfMonth(), last.value()));
            }
            cur = ym;
            last = p;
        }
        if (cur != null && last != null) out.add(new Pt(cur.atEndOfMonth(), last.value()));
        return out;
    }

    /** Annualised return of a holding that ends on each month-end, matching pandas shift. */
    public static List<Pt> rollingCagr(List<Pt> monthEnd, int years) {
        int shift = 12 * years;
        List<Pt> out = new ArrayList<>();
        for (int i = shift; i < monthEnd.size(); i++) {
            double a = monthEnd.get(i - shift).value();
            double b = monthEnd.get(i).value();
            if (a <= 0) continue;
            out.add(new Pt(monthEnd.get(i).date(), Math.pow(b / a, 1.0 / years) - 1));
        }
        return out;
    }

    public static double median(List<Double> values) {
        List<Double> xs = new ArrayList<>();
        for (Double v : values) if (v != null && !v.isNaN()) xs.add(v);
        if (xs.isEmpty()) return Double.NaN;
        xs.sort(Comparator.naturalOrder());
        int n = xs.size();
        if ((n & 1) == 1) return xs.get(n / 2);
        return (xs.get(n / 2 - 1) + xs.get(n / 2)) / 2.0;
    }

    public static Sip sip(List<Pt> series, double monthly, LocalDate start) {
        List<Pt> s = series;
        if (start != null) {
            s = new ArrayList<>();
            for (Pt p : series) if (!p.date().isBefore(start)) s.add(p);
        }
        if (s.isEmpty()) return null;
        List<Pt> buys = new ArrayList<>();
        YearMonth ym = null;
        for (Pt p : s) {
            YearMonth k = YearMonth.from(p.date());
            if (ym == null || !k.equals(ym)) {
                buys.add(p);
                ym = k;
            }
        }
        double units = 0;
        List<Pt> invPath = new ArrayList<>();
        List<Pt> valPath = new ArrayList<>();
        for (int i = 0; i < buys.size(); i++) {
            units += monthly / buys.get(i).value();
            invPath.add(new Pt(buys.get(i).date(), monthly * (i + 1) / 1e5));
            valPath.add(new Pt(buys.get(i).date(), units * buys.get(i).value() / 1e5));
        }
        double invested = monthly * buys.size();
        double value = units * s.get(s.size() - 1).value();
        List<Flow> flows = new ArrayList<>();
        for (Pt b : buys) flows.add(new Flow(b.date(), -monthly));
        flows.add(new Flow(s.get(s.size() - 1).date(), value));
        return new Sip(invested, value, buys.size(), xirr(flows), buys.get(0).date(), invPath, valPath);
    }

    public static Double xirr(List<Flow> flows) {
        if (flows == null || flows.isEmpty()) return null;
        LocalDate t0 = flows.get(0).date();
        try {
            double lo = -0.99, hi = 5.0;
            double nLo = npv(flows, t0, lo), nHi = npv(flows, t0, hi);
            if (nLo * nHi > 0) return null;
            double mid = 0;
            for (int i = 0; i < 200; i++) {
                mid = (lo + hi) / 2;
                double nMid = npv(flows, t0, mid);
                if (nLo * nMid <= 0) {
                    hi = mid;
                    nHi = nMid;
                } else {
                    lo = mid;
                    nLo = nMid;
                }
            }
            return mid;
        } catch (ArithmeticException ex) {
            return null;
        }
    }

    private static double npv(List<Flow> flows, LocalDate t0, double r) {
        double sum = 0;
        for (Flow f : flows) {
            double yrs = ChronoUnit.DAYS.between(t0, f.date()) / 365.25;
            sum += f.amount() / Math.pow(1 + r, yrs);
        }
        return sum;
    }

    public static double round1(double x) {
        return new BigDecimal(Double.toString(x)).setScale(1, RoundingMode.HALF_EVEN).doubleValue();
    }

    private static List<Pt> dropNonPositive(List<Pt> series) {
        List<Pt> out = new ArrayList<>();
        for (Pt p : series) if (p.value() > 0 && !Double.isNaN(p.value())) out.add(p);
        return out;
    }
}
