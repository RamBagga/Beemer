package com.beemer.service;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class DatasetsServiceTest {
    private static Map<String, Object> row(String period, String basis, String item, double v) {
        return Map.of("period_end", period, "basis", basis, "item", item, "value", v);
    }

    @Test
    void resultsPreferConsolidatedAndComputeYoY() {
        List<Map<String, Object>> rows = new ArrayList<>();
        String[] q = {"2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"};
        for (int i = 0; i < q.length; i++) {
            rows.add(row(q[i], "consolidated", "revenue", 100 + i * 10));
            rows.add(row(q[i], "consolidated", "net_profit", 20 + i));
            rows.add(row(q[i], "standalone", "revenue", 50));
        }
        rows.add(row("2026-06-30", "consolidated", "profit_owners", 25));
        Map<String, Object> r = DatasetsService.results(rows);
        assertEquals("consolidated", r.get("basis"));
        assertEquals(5, ((List<?>) r.get("quarters")).size());
        assertEquals(140.0 / 100 - 1, (Double) r.get("revenueYoY"), 1e-9);
        assertEquals(25.0 / 20 - 1, (Double) r.get("profitYoY"), 1e-9);   // owners' profit preferred
    }

    @Test
    void resultsEmptyWhenNoFilings() {
        Map<String, Object> r = DatasetsService.results(List.of());
        assertEquals(0, ((List<?>) r.get("quarters")).size());
        assertNull(r.get("revenueYoY"));
    }
}
