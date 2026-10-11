package com.beemer.math;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Port of analytics.clean_prices: drop one-day Yahoo glitches, then rescale earlier history
 * across an unadjusted split/demerger (a one-day move beyond ±30% while the market moved under 8%).
 */
public final class PriceCleaner {
    private PriceCleaner() {}

    public record Bar(LocalDate date, double close, double adj, double volume) {}

    public record Result(List<Bar> bars, List<String> notes) {}

    public static Result clean(List<Bar> input, Map<LocalDate, Double> marketReturn) {
        return clean(input, marketReturn, 0.30, 0.30);
    }

    public static Result clean(List<Bar> input, Map<LocalDate, Double> marketReturn, double spike, double ca) {
        List<Bar> df = new ArrayList<>();
        for (Bar b : input) if (b.close() > 0 && b.adj() > 0) df.add(b);
        List<String> notes = new ArrayList<>();
        for (int pass = 0; pass < 25; pass++) {
            double[] r = pct(df);
            List<Integer> bad = new ArrayList<>();
            for (int i = 0; i < df.size(); i++) {
                if (Double.isNaN(r[i])) continue;
                Double rn = (i + 1 < r.length && !Double.isNaN(r[i + 1])) ? r[i + 1] : null;
                if (rn == null) continue;
                boolean up = r[i] > spike && rn < -spike / (1 + spike);
                boolean down = r[i] < -spike / (1 + spike) && rn > spike;
                if (up || down) bad.add(i);
            }
            if (bad.isEmpty()) break;
            notes.add("dropped " + bad.size() + " glitch days");
            for (int k = bad.size() - 1; k >= 0; k--) df.remove((int) bad.get(k));
        }
        double[] r = pct(df);
        double[] volRatio = volumeRatio(df);
        for (int i = 0; i < df.size(); i++) {
            if (Double.isNaN(r[i]) || Math.abs(r[i]) <= ca) continue;
            double m = 0;
            if (marketReturn != null) {
                Double mv = marketReturn.get(df.get(i).date());
                if (mv != null && !mv.isNaN()) m = mv;
            }
            if (Math.abs(m) >= 0.08) continue;
            double vr = volRatio[i];
            if (!Double.isNaN(vr) && vr > 4 && df.get(i).date().getYear() >= 2010) {
                notes.add("kept " + df.get(i).date() + " move of " + signed0(r[i] * 100)
                        + "% as a real price move (volume " + IndianFormat.fixed(vr, 0) + "x normal)");
                continue;
            }
            double f = 1 + r[i];
            for (int j = 0; j < i; j++) {
                Bar b = df.get(j);
                df.set(j, new Bar(b.date(), b.close() * f, b.adj() * f, b.volume()));
            }
            notes.add("adjusted " + df.get(i).date() + " jump of " + signed0(r[i] * 100) + "% (likely split/demerger)");
        }
        return new Result(df, notes);
    }

    private static String signed0(double x) {
        String n = IndianFormat.fixed(x, 0);
        return n.startsWith("-") ? n : "+" + n;
    }

    private static double[] pct(List<Bar> df) {
        double[] r = new double[df.size()];
        if (df.isEmpty()) return r;
        r[0] = Double.NaN;
        for (int i = 1; i < df.size(); i++) {
            double prev = df.get(i - 1).adj();
            r[i] = prev == 0 ? Double.NaN : df.get(i).adj() / prev - 1;
        }
        return r;
    }

    /** rolling(20, min_periods=5).median().shift(1) of volume. */
    static double[] volumeRatio(List<Bar> df) {
        double[] out = new double[df.size()];
        for (int i = 0; i < df.size(); i++) {
            int from = Math.max(0, i - 20);
            int count = i - from;
            if (count < 5) {
                out[i] = Double.NaN;
                continue;
            }
            List<Double> w = new ArrayList<>(count);
            for (int j = from; j < i; j++) w.add(df.get(j).volume());
            double med = SeriesMath.median(w);
            out[i] = med == 0 ? Double.NaN : df.get(i).volume() / med;
        }
        return out;
    }
}
