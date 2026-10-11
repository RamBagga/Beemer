package com.beemer.data;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;

/**
 * Read-only access to the NSE datasets written by expand_data.py (shareholding, corporate actions, board
 * meetings, insider trades, deals, XBRL results, delivery, index valuations). Snapshots built before those
 * tables existed simply return empty lists.
 */
@Repository
public class DatasetsRepository {
    private final JdbcTemplate jdbc;

    public DatasetsRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public List<Map<String, Object>> rows(String sql, Object... args) {
        try {
            return jdbc.queryForList(sql, args);
        } catch (Exception e) {   // missing table on an older snapshot
            return List.of();
        }
    }

    public Long count(String table) {
        if (!table.matches("[a-z_]+")) throw new IllegalArgumentException("bad table");
        try {
            return jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Long.class);
        } catch (Exception e) {
            return null;
        }
    }

    public List<Map<String, Object>> shareholding(String symbol) {
        return rows("""
                SELECT period, promoter, public, fii, dii, mf, insurance, retail, hni, employee_trusts, pledge_flag, source
                FROM shareholding WHERE symbol=? AND substr(period, 6) IN ('03-31','06-30','09-30','12-31')
                ORDER BY period""", symbol);
    }

    public List<Map<String, Object>> corporateActions(String symbol) {
        return rows("SELECT ex_date, record_date, subject, kind, amount, ratio FROM corp_actions WHERE symbol=? ORDER BY ex_date DESC", symbol);
    }

    public List<Map<String, Object>> boardMeetings(String symbol, int limit) {
        return rows("""
                SELECT meeting_date, MAX(purpose) AS purpose, MAX(description) AS description FROM board_meetings
                WHERE symbol=? GROUP BY meeting_date ORDER BY meeting_date DESC LIMIT ?""", symbol, limit);
    }

    public List<Map<String, Object>> insider(String symbol, String since, int limit) {
        return rows("""
                SELECT person, category, txn_type, mode, qty, value, after_pct, to_date, disclosed_at FROM insider_trades
                WHERE symbol=? AND COALESCE(to_date, disclosed_at) >= ? AND mode IN ('Market Purchase', 'Market Sale')
                ORDER BY COALESCE(to_date, disclosed_at) DESC LIMIT ?""", symbol, since, limit);
    }

    public List<Map<String, Object>> deals(String symbol, int limit) {
        return rows("SELECT kind, date, client, side, qty, price FROM deals WHERE symbol=? ORDER BY date DESC LIMIT ?", symbol, limit);
    }

    public List<Map<String, Object>> results(String symbol) {
        return rows("SELECT period_end, basis, item, value FROM results_xbrl WHERE symbol=? ORDER BY period_end", symbol);
    }

    public List<Map<String, Object>> delivery(String symbol, int days) {
        return rows("""
                SELECT date, close, volume, deliv_pct FROM (SELECT date, close, volume, deliv_pct FROM delivery
                WHERE symbol=? AND series='EQ' ORDER BY date DESC LIMIT ?) ORDER BY date""", symbol, days);
    }

    public List<Map<String, Object>> indexLatest(List<String> names) {
        String in = String.join(",", names.stream().map(n -> "?").toList());
        return rows("""
                SELECT e.index_name, e.date, e.close, e.pct_change, e.pe, e.pb, e.div_yield FROM index_eod e
                JOIN (SELECT index_name, MAX(date) d FROM index_eod WHERE index_name IN (%s) GROUP BY index_name) m
                ON e.index_name=m.index_name AND e.date=m.d""".formatted(in), names.toArray());
    }

    public List<Map<String, Object>> indexHistory(String name, String since) {
        return rows("SELECT date, close, pe, pb, div_yield FROM index_eod WHERE index_name=? AND date>=? ORDER BY date", name, since);
    }

    public List<Map<String, Object>> sourceRuns() {
        return rows("""
                SELECT r.source, r.ts, r.status, r.rows, r.detail FROM source_runs r
                JOIN (SELECT source, MAX(ts) ts FROM source_runs GROUP BY source) m ON r.source=m.source AND r.ts=m.ts
                ORDER BY r.source""");
    }
}
