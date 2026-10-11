package com.beemer.data;

import com.beemer.math.FundamentalsSeries;
import com.beemer.math.PriceCleaner;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public class MarketRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper json;

    public MarketRepository(JdbcTemplate jdbc, ObjectMapper json) {
        this.jdbc = jdbc;
        this.json = json;
    }

    public boolean ready() {
        try {
            Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM company_metrics", Integer.class);
            return n != null && n > 0;
        } catch (Exception e) {
            return false;
        }
    }

    public List<Metric> metrics() {
        return jdbc.query("SELECT payload FROM company_metrics", (rs, i) -> new Metric(tree(rs.getString(1))));
    }

    public List<PriceCleaner.Bar> prices(String symbol) {
        return jdbc.query("SELECT date, close, adj_close, volume FROM prices WHERE symbol=? ORDER BY date",
                (rs, i) -> new PriceCleaner.Bar(LocalDate.parse(rs.getString(1).substring(0, 10)),
                        rs.getDouble(2), rs.getDouble(3), rs.getDouble(4)), symbol);
    }

    public List<FundamentalsSeries.Row> fundamentals(String symbol) {
        return jdbc.query("SELECT section, item, period, value FROM fundamentals WHERE symbol=?",
                (rs, i) -> new FundamentalsSeries.Row(rs.getString(1), rs.getString(2), rs.getString(3), rs.getDouble(4)), symbol);
    }

    private JsonNode tree(String raw) {
        try {
            return json.readTree(raw);
        } catch (Exception e) {
            throw new IllegalStateException("bad json payload", e);
        }
    }

    public String about(String symbol) {
        List<String> rows = jdbc.query("SELECT about FROM fund_meta WHERE symbol=?", (rs, i) -> rs.getString(1), symbol);
        return rows.isEmpty() ? null : rows.get(0);
    }

    public JsonNode picksMeta() {
        try {
            String run = jdbc.queryForObject("SELECT MAX(run_at) FROM picks", String.class);
            if (run == null) return null;
            String meta = jdbc.queryForObject("SELECT meta FROM picks_meta WHERE run_at=?", String.class, run);
            return meta == null ? null : tree(meta);
        } catch (Exception e) {
            return null;
        }
    }

    public List<JsonNode> picks() {
        try {
            String run = jdbc.queryForObject("SELECT MAX(run_at) FROM picks", String.class);
            if (run == null) return List.of();
            return jdbc.query("SELECT payload FROM picks WHERE run_at=? ORDER BY belt, rank",
                    (rs, i) -> tree(rs.getString(1)), run);
        } catch (Exception e) {
            return List.of();
        }
    }
}
