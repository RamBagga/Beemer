package com.beemer.data;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.ArrayList;
import java.util.List;

/** One company_metrics payload. Missing and JSON null are both null. */
public final class Metric {
    private final JsonNode n;

    public Metric(JsonNode n) { this.n = n; }

    public JsonNode node() { return n; }

    public String text(String k) {
        JsonNode v = n.get(k);
        return v == null || v.isNull() ? null : v.asText();
    }

    public Double num(String k) {
        JsonNode v = n.get(k);
        if (v == null || v.isNull() || !v.isNumber()) return null;
        double d = v.asDouble();
        return Double.isNaN(d) ? null : d;
    }

    public boolean flag(String k) {
        JsonNode v = n.get(k);
        if (v == null || v.isNull()) return false;
        if (v.isBoolean()) return v.booleanValue();
        if (v.isNumber()) return v.asDouble() != 0;
        return "true".equalsIgnoreCase(v.asText());
    }

    public String symbol() { return text("symbol"); }

    public List<JsonNode> subscores() {
        JsonNode raw = n.get("subscores_json");
        if (raw == null || raw.isNull()) return List.of();
        try {
            JsonNode parsed = raw.isTextual()
                    ? new com.fasterxml.jackson.databind.ObjectMapper().readTree(raw.asText())
                    : raw;
            List<JsonNode> out = new ArrayList<>();
            if (parsed.isArray()) parsed.forEach(out::add);
            return out;
        } catch (Exception e) {
            return List.of();
        }
    }
}
