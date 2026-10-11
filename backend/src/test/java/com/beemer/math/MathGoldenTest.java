package com.beemer.math;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MathGoldenTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final double EPS = 1e-6;

    private static JsonNode golden(String name) throws Exception {
        try (InputStream in = MathGoldenTest.class.getResourceAsStream("/golden/" + name)) {
            return JSON.readTree(in);
        }
    }

    private static List<SeriesMath.Pt> points(JsonNode dates, JsonNode values) {
        List<SeriesMath.Pt> out = new ArrayList<>();
        for (int i = 0; i < dates.size(); i++) {
            out.add(new SeriesMath.Pt(LocalDate.parse(dates.get(i).asText()), values.get(i).asDouble()));
        }
        return out;
    }

    @Test
    void niftyItMatchesPython() throws Exception {
        JsonNode g = golden("nifty_it.json");
        List<SeriesMath.Pt> s = points(g.get("dates"), g.get("values"));
        JsonNode cagr = g.get("cagr");
        for (int y : List.of(1, 3, 5, 10, 20)) {
            Double got = SeriesMath.cagr(s, y);
            JsonNode exp = cagr.get(String.valueOf(y));
            if (exp == null || exp.isNull()) assertNull(got, "cagr " + y);
            else assertClose(exp.asDouble(), got, "cagr " + y);
        }
        assertClose(cagr.get("max").asDouble(), SeriesMath.cagr(s, null), "cagr max");

        List<SeriesMath.Pt> dd = SeriesMath.drawdowns(s);
        assertClose(g.get("ddLast").asDouble(), dd.get(dd.size() - 1).value(), "dd last");
        SeriesMath.Pt min = dd.stream().min(java.util.Comparator.comparingDouble(SeriesMath.Pt::value)).orElseThrow();
        assertClose(g.get("ddMin").asDouble(), min.value(), "dd min");
        assertEquals(g.get("ddMinDate").asText(), min.date().toString());

        List<SeriesMath.Crash> crashes = SeriesMath.crashes(s, -0.2);
        assertEquals(g.get("crashes").size(), crashes.size(), "crash count");
        for (int i = 0; i < crashes.size(); i++) {
            JsonNode e = g.get("crashes").get(i);
            SeriesMath.Crash c = crashes.get(i);
            assertEquals(e.get("peak").asText(), c.peak().toString(), "peak " + i);
            assertEquals(e.get("trough").asText(), c.trough().toString(), "trough " + i);
            assertClose(e.get("fall").asDouble(), c.fallPct(), "fall " + i);
            assertClose(e.get("monthsDown").asDouble(), c.monthsDown(), "months down " + i);
            if (e.get("recovery").isNull()) assertNull(c.recovery());
            else {
                assertEquals(e.get("recovery").asText(), c.recovery().toString());
                assertClose(e.get("monthsRecover").asDouble(), c.monthsRecover(), "months recover " + i);
            }
        }

        JsonNode sipG = g.get("sip");
        SeriesMath.Sip sip = SeriesMath.sip(s, sipG.get("monthly").asDouble(), LocalDate.parse(sipG.get("start").asText()));
        assertEquals(sipG.get("months").asInt(), sip.months());
        assertClose(sipG.get("invested").asDouble(), sip.invested(), "invested");
        assertClose(sipG.get("value").asDouble(), sip.value(), "value");
        assertClose(sipG.get("xirr").asDouble(), sip.xirr(), "xirr");
        assertEquals(sipG.get("firstBuy").asText(), sip.start().toString());
        assertClose(sipG.get("pathFirst").get("val").asDouble(), sip.valuePath().get(0).value(), "path first");
        assertClose(sipG.get("pathLast").get("val").asDouble(), sip.valuePath().get(sip.valuePath().size() - 1).value(), "path last");
        assertClose(sipG.get("pathLast").get("inv").asDouble(), sip.investedPath().get(sip.investedPath().size() - 1).value(), "inv last");
        assertEquals(sipG.get("pathLast").get("date").asText(), sip.valuePath().get(sip.valuePath().size() - 1).date().toString());

        List<SeriesMath.Pt> me = SeriesMath.monthEndLast(s);
        assertEquals(g.get("monthEnd").get("n").asInt(), me.size());
        assertEquals(g.get("monthEnd").get("firstDate").asText(), me.get(0).date().toString());
        assertClose(g.get("monthEnd").get("first").asDouble(), me.get(0).value(), "me first");
        assertEquals(g.get("monthEnd").get("lastDate").asText(), me.get(me.size() - 1).date().toString());
        assertClose(g.get("monthEnd").get("last").asDouble(), me.get(me.size() - 1).value(), "me last");
        for (String y : List.of("1", "3", "5", "10")) {
            List<SeriesMath.Pt> roll = SeriesMath.rollingCagr(me, Integer.parseInt(y));
            JsonNode exp = g.get("rolling").get(y);
            assertEquals(exp.get("n").asInt(), roll.size(), "roll n " + y);
            long lost = roll.stream().filter(p -> p.value() < 0).count();
            long beat = roll.stream().filter(p -> p.value() > 0.10).count();
            assertClose(exp.get("lost").asDouble(), lost / (double) roll.size(), "lost " + y);
            assertClose(exp.get("beat10").asDouble(), beat / (double) roll.size(), "beat " + y);
            double worst = roll.stream().mapToDouble(SeriesMath.Pt::value).min().orElseThrow();
            double last = roll.get(roll.size() - 1).value();
            List<Double> vals = roll.stream().map(SeriesMath.Pt::value).toList();
            assertClose(exp.get("worst").asDouble(), worst, "worst " + y);
            assertClose(exp.get("median").asDouble(), SeriesMath.median(vals), "median " + y);
            assertClose(exp.get("last").asDouble(), last, "last " + y);
            assertEquals(exp.get("lastDate").asText(), roll.get(roll.size() - 1).date().toString());
        }
    }

    @Test
    void cleanPricesMatchesPython() throws Exception {
        JsonNode g = golden("clean_prices.json");
        assertClean(g);
        assertClean(g.get("rescale"));
    }

    private static void assertClean(JsonNode g) {
        List<PriceCleaner.Bar> bars = new ArrayList<>();
        Map<LocalDate, Double> mkt = new HashMap<>();
        for (int i = 0; i < g.get("dates").size(); i++) {
            LocalDate d = LocalDate.parse(g.get("dates").get(i).asText());
            bars.add(new PriceCleaner.Bar(d, g.get("close").get(i).asDouble(), g.get("adj").get(i).asDouble(), g.get("volume").get(i).asDouble()));
            mkt.put(d, g.get("marketReturn").get(i).asDouble());
        }
        PriceCleaner.Result r = PriceCleaner.clean(bars, mkt);
        assertEquals(g.get("expectedDates").size(), r.bars().size());
        for (int i = 0; i < r.bars().size(); i++) {
            assertEquals(g.get("expectedDates").get(i).asText(), r.bars().get(i).date().toString());
            assertClose(g.get("expectedAdj").get(i).asDouble(), r.bars().get(i).adj(), "adj " + i);
        }
        assertEquals(g.get("notes").size(), r.notes().size());
        for (int i = 0; i < r.notes().size(); i++) assertEquals(g.get("notes").get(i).asText(), r.notes().get(i));
    }

    @Test
    void formatsMatchPython() throws Exception {
        JsonNode g = golden("format.json");
        for (JsonNode c : g) {
            String fn = c.get("fn").asText();
            String exp = c.get("out").asText();
            String got = switch (fn) {
                case "pct" -> IndianFormat.pct(dbl(c.get("args").get(0)), c.get("args").get(1).asInt(), c.get("args").get(2).asBoolean());
                case "num" -> IndianFormat.num(dbl(c.get("args").get(0)), c.get("args").get(1).asInt());
                case "inr" -> IndianFormat.inr(dbl(c.get("args").get(0)), c.get("args").get(1).asInt());
                case "crore" -> IndianFormat.crore(dbl(c.get("args").get(0)));
                case "lakh" -> IndianFormat.lakh(c.get("args").get(0).asDouble());
                case "indian" -> IndianFormat.indian(c.get("args").get(0).asDouble(), c.get("args").get(1).asInt());
                default -> throw new IllegalStateException(fn);
            };
            assertEquals(exp, got, fn + " " + c.get("args"));
        }
    }

    @Test
    void screenerFiltersMatchPython() throws Exception {
        JsonNode g = golden("screener.json");
        List<ScreenerFilter.Row> rows = new ArrayList<>();
        for (JsonNode r : g.get("rows")) {
            rows.add(new ScreenerFilter.Row(r.get("symbol").asText(), r.get("subsector").asText(),
                    dbl(r.get("buffett_score")), dbl(r.get("pe")), dbl(r.get("debt_to_equity")),
                    dbl(r.get("roe_median_10y")), r.get("profitable_ttm").asBoolean(),
                    r.get("young_listing").asBoolean(), dbl(r.get("margin_of_safety"))));
        }
        for (JsonNode c : g.get("cases")) {
            List<String> pick = new ArrayList<>();
            if (c.has("pick")) c.get("pick").forEach(p -> pick.add(p.asText()));
            ScreenerFilter.Query q = new ScreenerFilter.Query(pick,
                    c.path("minScore").asInt(0), c.path("maxPe").asDouble(150), c.path("maxDe").asDouble(2),
                    c.path("minRoe").asInt(0), c.path("profitable").asBoolean(false),
                    c.path("seasoned").asBoolean(false), c.path("belowValue").asBoolean(false));
            List<String> got = ScreenerFilter.apply(rows, q).stream().map(ScreenerFilter.Row::symbol).toList();
            List<String> exp = new ArrayList<>();
            c.get("expect").forEach(x -> exp.add(x.asText()));
            assertEquals(exp, got, c.get("name").asText());
        }
    }

    @Test
    void peHistoryMatchesPython() throws Exception {
        JsonNode g = golden("pe_history.json");
        List<SeriesMath.Pt> closes = new ArrayList<>();
        List<SeriesMath.Pt> profits = new ArrayList<>();
        for (JsonNode c : g.get("closes")) closes.add(new SeriesMath.Pt(LocalDate.parse(c.get("date").asText()), c.get("close").asDouble()));
        for (JsonNode c : g.get("profits")) profits.add(new SeriesMath.Pt(LocalDate.parse(c.get("date").asText()), c.get("profit").asDouble()));
        PeHistory.Result r = PeHistory.compute(closes, profits, g.get("npTtm").asDouble(), g.get("epsTtm").asDouble());
        assertEquals(g.get("peHist").size(), r.points().size());
        for (int i = 0; i < r.points().size(); i++) {
            assertClose(g.get("peHist").get(i).get("pe").asDouble(), r.points().get(i).pe(), "pe " + i);
        }
        assertClose(g.get("median").asDouble(), r.median(), "median");
        assertClose(g.get("vsHistory").asDouble(), PeHistory.vsHistory(g.get("peToday").asDouble(), r.median()), "vs");
    }

    @Test
    void infyFundamentalChartsMatchPython() throws Exception {
        JsonNode g = golden("infy_fund.json");
        List<FundamentalsSeries.Row> rows = new ArrayList<>();
        for (JsonNode r : g.get("funds")) {
            rows.add(new FundamentalsSeries.Row(r.get("section").asText(), r.get("item").asText(), r.get("period").asText(), r.get("value").asDouble()));
        }
        List<SeriesMath.Pt> closes = new ArrayList<>();
        for (JsonNode c : g.get("closes")) closes.add(new SeriesMath.Pt(LocalDate.parse(c.get("date").asText()), c.get("close").asDouble()));
        FundamentalsSeries.Charts charts = FundamentalsSeries.charts(rows, closes);
        assertSeries(g.get("sales"), charts.sales(), "sales");
        assertSeries(g.get("profit"), charts.profit(), "profit");
        assertSeries(g.get("opm"), charts.opm(), "opm");
        assertSeries(g.get("roePct"), charts.roePct(), "roe");
        assertSeries(g.get("roce"), charts.roce(), "roce");
        assertSeries(g.get("peHist"), charts.peHist(), "pe");
        assertSeries(g.get("fcf"), charts.fcf(), "fcf");
    }

    private static void assertSeries(JsonNode exp, List<FundamentalsSeries.Point> got, String label) {
        assertEquals(exp.size(), got.size(), label + " length");
        for (int i = 0; i < got.size(); i++) {
            JsonNode e = exp.get(i);
            if (e.get("year").isNull()) assertNull(got.get(i).year());
            else assertEquals(e.get("year").asInt(), got.get(i).year(), label + " year " + i);
            if (e.get("value").isNull()) assertNull(got.get(i).value(), label + " " + i);
            else assertClose(e.get("value").asDouble(), got.get(i).value(), label + " " + i);
        }
    }

    private static Double dbl(JsonNode n) {
        return n == null || n.isNull() ? null : n.asDouble();
    }

    private static void assertClose(double exp, Double got, String label) {
        assertTrue(got != null && Math.abs(exp - got) < EPS, label + " expected " + exp + " got " + got);
    }
}
