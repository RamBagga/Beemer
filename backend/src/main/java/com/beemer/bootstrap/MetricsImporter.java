package com.beemer.bootstrap;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/** One-shot parquet → company_metrics import. Request-time reads stay on sqlite-jdbc. */
public final class MetricsImporter {
    private static final ObjectMapper JSON = new ObjectMapper();

    public int importParquet(Path db, Path parquet) throws Exception {
        List<String> lines = readJson(parquet);
        try (Connection c = DriverManager.getConnection("jdbc:sqlite:" + db)) {
            try (Statement st = c.createStatement()) {
                st.execute("DROP TABLE IF EXISTS company_metrics");
                st.execute("""
                        CREATE TABLE company_metrics(
                          symbol TEXT PRIMARY KEY, name TEXT, subsector TEXT, theme TEXT, industry TEXT,
                          buffett_score REAL, score_label TEXT, payload TEXT)""");
            }
            try (PreparedStatement ps = c.prepareStatement("INSERT INTO company_metrics VALUES (?,?,?,?,?,?,?,?)")) {
                for (String line : lines) {
                    JsonNode n = JSON.readTree(line);
                    ps.setString(1, text(n, "symbol"));
                    ps.setString(2, text(n, "name"));
                    ps.setString(3, text(n, "subsector"));
                    ps.setString(4, text(n, "theme"));
                    ps.setString(5, text(n, "industry"));
                    if (n.hasNonNull("buffett_score") && n.get("buffett_score").isNumber()) ps.setDouble(6, n.get("buffett_score").asDouble());
                    else ps.setNull(6, java.sql.Types.REAL);
                    ps.setString(7, text(n, "score_label"));
                    ps.setString(8, line);
                    ps.addBatch();
                }
                ps.executeBatch();
            }
        }
        return lines.size();
    }

    private static List<String> readJson(Path parquet) throws Exception {
        String path = parquet.toAbsolutePath().toString().replace("'", "''");
        List<String> lines = new ArrayList<>();
        try (Connection duck = DriverManager.getConnection("jdbc:duckdb:");
             Statement st = duck.createStatement();
             ResultSet rs = st.executeQuery("SELECT to_json(t) FROM read_parquet('" + path + "') t")) {
            while (rs.next()) lines.add(rs.getString(1));
        }
        return lines;
    }

    private static String text(JsonNode n, String k) {
        JsonNode v = n.get(k);
        return v == null || v.isNull() ? null : v.asText();
    }
}
