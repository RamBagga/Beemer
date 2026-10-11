package com.beemer.service;

import com.beemer.data.DatasetsRepository;
import com.beemer.math.SeriesMath;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Company filings (ownership, dividends, actions, meetings, insider trades, deals, official results)
 *  and market context (NSE index valuations), shaped for the React pages. */
@Service
public class DatasetsService {
    private static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    public static final List<String> CONTEXT = List.of("Nifty 50", "Nifty IT", "Nifty 500", "Nifty Midcap 150",
            "Nifty Smallcap 250", "Nifty Bank", "Nifty India Digital", "Nifty MidSmall IT & Telecom");
    private static final String[] TABLES = {"universe_all", "prices", "fundamentals", "delivery", "index_eod",
            "corp_actions", "board_meetings", "shareholding", "insider_trades", "deals", "results_xbrl"};

    private final DatasetsRepository repo;

    public DatasetsService(DatasetsRepository repo) { this.repo = repo; }

    static LocalDate today() { return LocalDate.now(IST); }

    @Cacheable(value = "filings", key = "#symbol")
    public Map<String, Object> filings(String symbol) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("symbol", symbol);
        out.put("ownership", repo.shareholding(symbol));

        List<Map<String, Object>> actions = repo.corporateActions(symbol);
        Map<Integer, Double> perFy = new TreeMap<>();
        List<Map<String, Object>> other = new ArrayList<>();
        for (Map<String, Object> a : actions) {
            String kind = String.valueOf(a.get("kind"));
            LocalDate ex = LocalDate.parse(String.valueOf(a.get("ex_date")));
            if (kind.startsWith("dividend") && a.get("amount") instanceof Number n) {
                int fy = ex.getMonthValue() >= 4 ? ex.getYear() + 1 : ex.getYear();   // Indian FY ends in March
                perFy.merge(fy, n.doubleValue(), Double::sum);
            }
            if (!kind.startsWith("dividend") && !"agm".equals(kind) && !"other".equals(kind)) other.add(a);
        }
        List<Map<String, Object>> divs = new ArrayList<>();
        perFy.forEach((fy, v) -> {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("fy", "FY" + String.valueOf(fy).substring(2));
            d.put("year", fy);
            d.put("perShare", Math.round(v * 100) / 100.0);
            divs.add(d);
        });
        out.put("dividends", divs);
        out.put("actions", other);
        out.put("dividendEvents", actions.stream().filter(a -> String.valueOf(a.get("kind")).startsWith("dividend")).limit(12).toList());

        List<Map<String, Object>> meetings = repo.boardMeetings(symbol, 12);
        String t = today().toString();
        out.put("nextMeeting", meetings.stream().filter(m -> String.valueOf(m.get("meeting_date")).compareTo(t) >= 0)
                .reduce((a, b) -> b).orElse(null));
        out.put("meetings", meetings.stream().filter(m -> String.valueOf(m.get("meeting_date")).compareTo(t) < 0).limit(6).toList());

        out.put("insider", repo.insider(symbol, today().minusYears(2).toString(), 15));
        out.put("deals", repo.deals(symbol, 15));
        out.put("results", results(repo.results(symbol)));
        out.put("delivery", repo.delivery(symbol, 250));
        return out;
    }

    /** XBRL rows -> quarterly series, consolidated where filed, else standalone. */
    static Map<String, Object> results(List<Map<String, Object>> rows) {
        Map<String, Map<String, Map<String, Double>>> by = new TreeMap<>();   // period -> basis -> item -> value
        for (Map<String, Object> r : rows) {
            if (!(r.get("value") instanceof Number v)) continue;
            by.computeIfAbsent(String.valueOf(r.get("period_end")), k -> new LinkedHashMap<>())
                    .computeIfAbsent(String.valueOf(r.get("basis")), k -> new LinkedHashMap<>())
                    .put(String.valueOf(r.get("item")), v.doubleValue());
        }
        boolean anyConsol = by.values().stream().anyMatch(b -> b.containsKey("consolidated"));
        List<String> q = new ArrayList<>();
        List<Double> rev = new ArrayList<>(), np = new ArrayList<>(), margin = new ArrayList<>(), eps = new ArrayList<>();
        for (var e : by.entrySet()) {
            Map<String, Double> it = e.getValue().get(anyConsol ? "consolidated" : "standalone");
            if (it == null || it.get("revenue") == null) continue;
            q.add(e.getKey());
            Double r = it.get("revenue");
            Double p = it.getOrDefault("profit_owners", it.get("net_profit"));
            rev.add(round(r));
            np.add(round(p));
            margin.add(p == null || r == null || r == 0 ? null : Math.round(p / r * 1000) / 10.0);
            eps.add(it.get("eps"));
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("basis", anyConsol ? "consolidated" : "standalone");
        out.put("quarters", q);
        out.put("revenue", rev);
        out.put("profit", np);
        out.put("margin", margin);
        out.put("eps", eps);
        if (q.size() >= 5) {
            int n = q.size() - 1;
            Double now = rev.get(n), ago = rev.get(n - 4), pn = np.get(n), pa = np.get(n - 4);
            out.put("revenueYoY", now == null || ago == null || ago == 0 ? null : now / ago - 1);
            out.put("profitYoY", pn == null || pa == null || pa <= 0 ? null : pn / pa - 1);
        }
        return out;
    }

    private static Double round(Double v) { return v == null ? null : Math.round(v * 10) / 10.0; }

    @Cacheable("market")
    public Map<String, Object> market() {
        List<Map<String, Object>> latest = repo.indexLatest(CONTEXT);
        String since = today().minusYears(10).toString();
        List<Map<String, Object>> rows = new ArrayList<>();
        for (String name : CONTEXT) {
            Map<String, Object> l = latest.stream().filter(r -> name.equals(r.get("index_name"))).findFirst().orElse(null);
            if (l == null) continue;
            List<Map<String, Object>> hist = repo.indexHistory(name, since);
            List<Double> pes = new ArrayList<>();
            List<SeriesMath.Pt> closes = new ArrayList<>();
            for (Map<String, Object> h : hist) {
                if (h.get("pe") instanceof Number p && p.doubleValue() > 0) pes.add(p.doubleValue());
                if (h.get("close") instanceof Number c) closes.add(new SeriesMath.Pt(LocalDate.parse(String.valueOf(h.get("date"))), c.doubleValue()));
            }
            Map<String, Object> r = new LinkedHashMap<>(l);
            r.put("name", name);
            r.put("peMedian", pes.isEmpty() ? null : SeriesMath.median(pes));
            r.put("historyFrom", hist.isEmpty() ? null : hist.get(0).get("date"));
            r.put("change1y", change(closes, 1));
            rows.add(r);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("indices", rows);
        out.put("asOf", rows.stream().map(r -> String.valueOf(r.get("date"))).max(String::compareTo).orElse(null));
        return out;
    }

    private static Double change(List<SeriesMath.Pt> s, int years) {
        if (s.size() < 2) return null;
        SeriesMath.Pt last = s.get(s.size() - 1);
        LocalDate target = last.date().minusYears(years);
        SeriesMath.Pt base = null;
        for (SeriesMath.Pt p : s) if (!p.date().isAfter(target)) base = p;
        return base == null || base.value() == 0 ? null : last.value() / base.value() - 1;
    }

    @Cacheable("inventory")
    public Map<String, Object> inventory() {
        Map<String, Object> counts = new LinkedHashMap<>();
        for (String t : TABLES) counts.put(t, repo.count(t));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("tables", counts);
        out.put("sources", repo.sourceRuns());
        return out;
    }
}
