package com.beemer.service;

import com.beemer.data.MarketRepository;
import com.beemer.data.Metric;
import com.beemer.math.IndianFormat;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class PicksService {
    private static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    private static final DateTimeFormatter UPDATED = DateTimeFormatter.ofPattern("dd MMM yyyy, h:mm a", Locale.ENGLISH).withZone(IST);
    private static final List<String> ORDER = List.of("short", "long", "volatile");
    private static final Map<String, String[]> COPY = Map.of(
            "short", new String[]{"Momentum", "1–3 months", "Outpacing Nifty IT, with trend and results behind it."},
            "long", new String[]{"Compounders", "5 years +", "Quality businesses at sensible prices."},
            "volatile", new String[]{"Movers", "Last 5 days", "The largest unusual moves, up and down."});

    private final MarketRepository repo;
    private final MetricsService metrics;

    public PicksService(MarketRepository repo, MetricsService metrics) {
        this.repo = repo;
        this.metrics = metrics;
    }

    @Cacheable("picks")
    public Map<String, Object> view() {
        List<JsonNode> rows = repo.picks();
        JsonNode meta = repo.picksMeta();
        Map<String, Object> out = new LinkedHashMap<>();
        if (rows.isEmpty() || meta == null) {
            out.put("empty", true);
            return out;
        }
        Map<String, String> names = new LinkedHashMap<>();
        try {
            for (Metric m : metrics.all()) names.put(m.symbol(), m.text("name"));
        } catch (Exception ignored) {}
        String generated = meta.path("generated_at").asText("");
        String updated = generated;
        try {
            updated = UPDATED.format(OffsetDateTime.parse(generated)) + " IST";
        } catch (Exception ignored) {}
        String asOf = meta.path("as_of").asText(null);
        out.put("empty", false);
        out.put("updated", updated);
        out.put("run", generated);
        out.put("asOf", asOf == null ? null : IndianFormat.dayMonthYear(java.time.LocalDate.parse(asOf.substring(0, 10))));
        JsonNode elig = meta.path("eligible");
        JsonNode changes = meta.path("changes");
        JsonNode bt = meta.get("backtest");
        List<Map<String, Object>> belts = new ArrayList<>();
        int n = 1;
        for (String belt : ORDER) {
            List<JsonNode> cards = new ArrayList<>();
            for (JsonNode row : rows) if (belt.equals(row.path("belt").asText())) cards.add(row);
            if (cards.isEmpty()) continue;
            String[] copy = COPY.get(belt);
            Map<String, Object> b = new LinkedHashMap<>();
            b.put("id", belt);
            b.put("n", n++);
            b.put("title", copy[0]);
            b.put("horizon", copy[1]);
            b.put("blurb", copy[2]);
            b.put("eligible", elig.path(belt).isMissingNode() ? null : elig.path(belt).asInt());
            b.put("universe", elig.path("universe").isMissingNode() ? null : elig.path("universe").asInt());
            JsonNode ch = changes.path(belt);
            List<String> previous = new ArrayList<>();
            List<String> entered = new ArrayList<>();
            if (ch.isObject()) {
                ch.path("previous").forEach(x -> previous.add(x.asText()));
                ch.path("entered").forEach(x -> entered.add(x.asText()));
            }
            b.put("previous", previous);
            b.put("entered", entered);
            Map<String, String> prevNames = new LinkedHashMap<>();
            for (String s : previous) prevNames.put(s, names.getOrDefault(s, ""));
            b.put("names", prevNames);
            b.put("note", note(belt, bt));
            List<Map<String, Object>> cardOut = new ArrayList<>();
            for (JsonNode c : cards) cardOut.add(card(c));
            b.put("cards", cardOut);
            belts.add(b);
        }
        out.put("belts", belts);
        out.put("backtest", bt);
        out.put("trackRecord", track(bt));
        return out;
    }

    static String note(String belt, JsonNode bt) {
        JsonNode b = bt == null ? null : bt.get(belt);
        if ("long".equals(belt)) return "Not backtested. Today's fundamentals can't be applied to past prices without hindsight.";
        if (b == null || b.isNull()) return "";
        String from = b.path("from").asText("");
        String year = from.length() >= 4 ? from.substring(from.length() - 4) : from;
        if ("short".equals(belt) && b.has("hit_rate_3m")) {
            return "Since " + year + ": beat the median stock over 3 months in <b>" + IndianFormat.fixed(b.get("hit_rate_3m").asDouble() * 100, 0)
                    + "%</b> of months (median " + IndianFormat.signed(b.get("median_excess_3m").asDouble() * 100, 1)
                    + " pts). Over 1 month, " + IndianFormat.fixed(b.get("hit_rate_1m").asDouble() * 100, 0) + "%.";
        }
        if ("volatile".equals(belt) && b.has("after_down_1m_excess")) {
            return "Since " + year + ": next month vs median, " + IndianFormat.signed(b.get("after_down_1m_excess").asDouble() * 100, 1)
                    + " pts after sharp falls, " + IndianFormat.signed(b.get("after_up_1m_excess").asDouble() * 100, 1)
                    + " pts after sharp rises. Sharp moves often partly reverse.";
        }
        return "";
    }

    static String track(JsonNode bt) {
        if (bt == null) return null;
        JsonNode sb = bt.get("short");
        if (sb == null || !sb.has("hit_rate_3m")) return null;
        JsonNode vb = bt.get("volatile");
        String s = "<b>Track record, " + sb.get("from").asText() + " to " + sb.get("to").asText() + ".</b> Momentum top 5 beat the median stock over 3 months in <b>"
                + IndianFormat.fixed(sb.get("hit_rate_3m").asDouble() * 100, 0) + "%</b> of months (median "
                + IndianFormat.signed(sb.get("median_excess_3m").asDouble() * 100, 1) + " pts). Over 1 month: "
                + IndianFormat.fixed(sb.get("hit_rate_1m").asDouble() * 100, 0) + "%. ";
        if (vb != null && vb.has("after_down_1m_excess")) {
            s += "After sharp falls, Movers did " + IndianFormat.signed(vb.get("after_down_1m_excess").asDouble() * 100, 1) + " pts vs median the next month. ";
        }
        return s + "Compounders not backtested. Price-only test on today's list, so results flatter slightly.";
    }

    private static Map<String, Object> card(JsonNode c) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("symbol", c.path("symbol").asText());
        m.put("name", c.path("name").asText());
        m.put("subsector", c.path("subsector").asText(null));
        m.put("price", c.path("price").asDouble());
        m.put("chg1d", c.hasNonNull("chg_1d") ? c.get("chg_1d").asDouble() : null);
        m.put("score", c.path("score").asDouble());
        m.put("buffettScore", c.hasNonNull("buffett_score") ? c.get("buffett_score").asDouble() : null);
        m.put("reason", c.path("reason").asText(""));
        m.put("statLabel", c.path("stat_label").asText());
        m.put("stat", c.hasNonNull("stat") ? c.get("stat").asDouble() : null);
        m.put("direction", c.path("direction").asText("up"));
        m.put("rank", c.path("rank").asInt());
        List<Double> spark = new ArrayList<>();
        JsonNode sp = c.get("spark");
        if (sp != null && sp.isTextual()) {
            try {
                sp = new com.fasterxml.jackson.databind.ObjectMapper().readTree(sp.asText());
            } catch (Exception ignored) {}
        }
        if (sp != null && sp.isArray()) sp.forEach(x -> spark.add(x.asDouble()));
        m.put("spark", spark);
        return m;
    }
}
