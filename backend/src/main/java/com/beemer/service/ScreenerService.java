package com.beemer.service;

import com.beemer.data.Metric;
import com.beemer.math.IndianFormat;
import com.beemer.math.ScreenerFilter;
import com.beemer.math.SeriesMath;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ScreenerService {
    private final MetricsService metrics;

    public ScreenerService(MetricsService metrics) { this.metrics = metrics; }

    @Cacheable(value = "screener", key = "#q")
    public Map<String, Object> screen(ScreenerFilter.Query q) {
        List<Metric> all = metrics.all();
        List<ScreenerFilter.Row> rows = new ArrayList<>();
        Map<String, Metric> by = new LinkedHashMap<>();
        for (Metric m : all) {
            by.put(m.symbol(), m);
            rows.add(new ScreenerFilter.Row(m.symbol(), m.text("subsector"), m.num("buffett_score"), m.num("pe"),
                    m.num("debt_to_equity"), m.num("roe_median_10y"), m.flag("profitable_ttm"), m.flag("young_listing"),
                    m.num("margin_of_safety")));
        }
        List<ScreenerFilter.Row> kept = ScreenerFilter.apply(rows, q);
        List<Map<String, Object>> outRows = new ArrayList<>();
        List<Double> pes = new ArrayList<>();
        int pass = 0, prof = 0;
        List<Map<String, Object>> dots = new ArrayList<>();
        for (ScreenerFilter.Row row : kept) {
            Metric m = by.get(row.symbol());
            if (m.num("buffett_score") != null && m.num("buffett_score") >= 60) pass++;
            if (m.flag("profitable_ttm")) prof++;
            if (m.num("pe") != null) pes.add(m.num("pe"));
            outRows.add(row(m));
            Double pe = m.num("pe");
            Double roe = m.num("roe_median_10y");
            if (pe != null && roe != null && pe <= 200) {
                Map<String, Object> d = new LinkedHashMap<>();
                d.put("symbol", m.symbol());
                d.put("name", m.text("name"));
                d.put("pe", pe);
                d.put("roe", roe * 100);
                d.put("score", m.num("buffett_score"));
                d.put("mcap", m.num("market_cap_cr"));
                dots.add(d);
            }
        }
        Double medPe = pes.isEmpty() ? null : SeriesMath.median(pes);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("matches", kept.size());
        out.put("score60", pass);
        out.put("profitable", prof);
        out.put("medianPe", medPe);
        out.put("callout", "<b>" + kept.size() + "</b> matches. <b>" + pass + "</b> score 60+. <b>" + prof
                + "</b> profitable. Median P/E <b>" + (medPe == null ? "–" : IndianFormat.fixed(medPe, 1)) + "</b>.");
        out.put("rows", outRows);
        out.put("scatter", dots);
        out.put("subsectors", all.stream().map(m -> m.text("subsector")).filter(s -> s != null).distinct().sorted().toList());
        return out;
    }

    private static Map<String, Object> row(Metric m) {
        Map<String, Object> r = new LinkedHashMap<>();
        r.put("symbol", m.symbol());
        r.put("name", m.text("name"));
        r.put("subsector", m.text("subsector"));
        r.put("score", m.num("buffett_score"));
        r.put("verdict", m.text("score_label"));
        r.put("roeTest", m.num("sub_roe"));
        r.put("debtTest", m.num("sub_debt"));
        r.put("growthTest", m.num("sub_growth"));
        r.put("moatTest", m.num("sub_moat"));
        r.put("cashTest", m.num("sub_fcf"));
        r.put("priceTest", m.num("sub_value"));
        r.put("listed", m.num("listing_year") == null ? null : m.num("listing_year").intValue());
        r.put("profitable", m.flag("profitable_ttm"));
        r.put("roe", m.num("roe_median_10y"));
        r.put("roce", m.num("roce_median_10y"));
        r.put("debt", m.num("debt_to_equity"));
        r.put("sales3", m.num("sales_cagr_3y"));
        r.put("profit5", m.num("profit_cagr_5y"));
        r.put("opm", m.num("opm_median_10y"));
        r.put("pe", m.num("pe"));
        r.put("peVs", m.num("pe_vs_history"));
        r.put("dy", m.num("dividend_yield"));
        r.put("mos", m.num("margin_of_safety"));
        r.put("cagr1", m.num("cagr_1y"));
        r.put("cagr5", m.num("cagr_5y"));
        r.put("maxDd", m.num("max_drawdown"));
        r.put("mcap", m.num("market_cap_cr"));
        return r;
    }
}
