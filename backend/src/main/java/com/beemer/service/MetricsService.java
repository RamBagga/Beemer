package com.beemer.service;

import com.beemer.api.NoDataException;
import com.beemer.data.MarketRepository;
import com.beemer.data.Metric;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class MetricsService {
    private final MarketRepository repo;

    public MetricsService(MarketRepository repo) { this.repo = repo; }

    @Cacheable("metrics")
    public List<Metric> all() {
        if (!repo.ready()) throw new NoDataException();
        List<Metric> rows = repo.metrics();
        if (rows.isEmpty()) throw new NoDataException();
        return rows;
    }

    /** The curated 64 (tier core). Snapshots built before the extended universe have no tier: all core. */
    public List<Metric> core() {
        return all().stream().filter(MetricsService::isCore).toList();
    }

    /** scope "all" = every tech name; anything else = core. */
    public List<Metric> scope(String scope) {
        return "all".equalsIgnoreCase(scope) ? all() : core();
    }

    public static boolean isCore(Metric m) {
        String t = m.text("tier");
        return t == null || "core".equals(t);
    }
}
